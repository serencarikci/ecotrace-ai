from __future__ import annotations
import re
import uuid
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.ai_constants import SAFE_AI_ACTIONS
from ecotrace.core.exceptions import ValidationAppError
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonInventory
from ecotrace.modules.digital_product_passport.infrastructure.models import DigitalProductPassport
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.product_carbon_footprint.infrastructure.models import ProductCarbonFootprint
from ecotrace.modules.products.infrastructure.models import Product
from ecotrace.modules.scenarios.infrastructure.models import ScenarioModel as Scenario
from ecotrace.modules.sustainability_targets.infrastructure.models import SustainabilityTarget
from ecotrace.shared.application.org_access import require_ai_read

def detect_safe_actions(question: str) -> list[str]:
    q = question.lower()
    actions: list[str] = []
    mapping = [('summarize_inventory', ('inventory', 'envanter', 'özetle inventory')), ('compare_inventories', ('compare invent', 'envanter karşılaştır')), ('explain_emission_increase', ('increase', 'artış', 'neden artt')), ('highest_emitting_facility', ('highest', 'en yüksek', 'facility', 'tesis')), ('explain_scope_breakdown', ('scope', 'kapsam')), ('summarize_product_footprint', ('footprint', 'ayak izi', 'pcf')), ('summarize_passport', ('passport', 'pasaport', 'dpp')), ('compare_products', ('compare product', 'ürün karşılaştır')), ('compare_scenarios', ('scenario', 'senaryo')), ('explain_target_progress', ('target', 'hedef')), ('generate_sustainability_summary', ('sustainability summary', 'sürdürülebilirlik özeti')), ('find_related_documents', ('related document', 'ilgili belge')), ('locate_evidence', ('evidence', 'kanıt', 'locate'))]
    for action, keys in mapping:
        if any((k in q for k in keys)) and action in SAFE_AI_ACTIONS:
            actions.append(action)
    return actions[:3]

def run_tools(db: Session, user: User, organization_id: uuid.UUID, *, question: str, actions: list[str] | None=None) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    selected = actions or detect_safe_actions(question)
    results: list[dict[str, Any]] = []
    for action in selected:
        if action not in SAFE_AI_ACTIONS:
            raise ValidationAppError(f'Destructive or unsupported AI action: {action}')
        handler = _HANDLERS.get(action)
        if handler is None:
            continue
        payload = handler(db, organization_id, question)
        results.append({'action': action, 'result': payload})
    return results

def tool_evidence_blocks(tool_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for idx, item in enumerate(tool_results, start=1):
        result = item.get('result') or {}
        summary = result.get('summary') or str(result)
        blocks.append({'label': f'T{idx}', 'documentName': f"tool:{item['action']}", 'documentId': None, 'pageNumber': None, 'chunkId': None, 'databaseSource': 'structured', 'recordId': result.get('recordId'), 'url': result.get('url'), 'score': 1.0, 'snippet': summary[:400], 'content': summary})
    return blocks

def _summarize_inventory(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    inv = db.execute(select(CarbonInventory).where(CarbonInventory.organization_id == organization_id).order_by(CarbonInventory.updated_at.desc()).limit(1)).scalar_one_or_none()
    if inv is None:
        return {'summary': 'No carbon inventory found for this organization.', 'recordId': None}
    total = getattr(inv, 'total_emissions_kg_co2e', None)
    summary = f"Carbon inventory '{inv.name}' status={inv.status}. Total emissions kgCO2e={total}."
    return {'summary': summary, 'recordId': str(inv.id), 'name': inv.name, 'status': inv.status}

def _highest_facility(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    count = db.execute(select(func.count()).select_from(Facility).where(Facility.organization_id == organization_id)).scalar_one()
    facilities = list(db.execute(select(Facility).where(Facility.organization_id == organization_id).order_by(Facility.name.asc()).limit(5)).scalars())
    names = ', '.join((f.name for f in facilities)) or 'none'
    return {'summary': f'Organization has {count} facilities. Sample facilities: {names}. Detailed emission ranking requires an approved calculation run.', 'recordId': str(facilities[0].id) if facilities else None}

def _scope_breakdown(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    inv = _summarize_inventory(db, organization_id, question)
    return {'summary': f"{inv['summary']} Scope breakdown should be read from approved calculation analytics endpoints; chat tools only surface authorized structured summaries.", 'recordId': inv.get('recordId')}

def _summarize_product_footprint(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    row = db.execute(select(ProductCarbonFootprint).where(ProductCarbonFootprint.organization_id == organization_id).order_by(ProductCarbonFootprint.updated_at.desc()).limit(1)).scalar_one_or_none()
    if row is None:
        return {'summary': 'No product carbon footprint records found.', 'recordId': None}
    value = getattr(row, 'total_kg_co2e', None) or getattr(row, 'result_kg_co2e', None)
    return {'summary': f'Latest PCF status={row.status}, total_kg_co2e={value}.', 'recordId': str(row.id)}

def _summarize_passport(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    row = db.execute(select(DigitalProductPassport).where(DigitalProductPassport.organization_id == organization_id).order_by(DigitalProductPassport.updated_at.desc()).limit(1)).scalar_one_or_none()
    if row is None:
        return {'summary': 'No digital product passport found.', 'recordId': None}
    return {'summary': f"Passport '{row.title}' code={row.passport_code} status={row.status} public_slug={row.public_slug}.", 'recordId': str(row.id), 'url': f'/passport/{row.public_slug}'}

def _compare_products(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    products = list(db.execute(select(Product).where(Product.organization_id == organization_id, Product.is_active.is_(True)).order_by(Product.name.asc()).limit(5)).scalars())
    summary = '; '.join((f'{p.code}:{p.name}' for p in products)) or 'No products'
    return {'summary': f'Products available for comparison: {summary}', 'recordId': None}

def _compare_scenarios(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    rows = list(db.execute(select(Scenario).where(Scenario.organization_id == organization_id).order_by(Scenario.updated_at.desc()).limit(5)).scalars())
    summary = '; '.join((f'{r.name} ({r.status})' for r in rows)) or 'No scenarios'
    return {'summary': f'Scenarios: {summary}', 'recordId': str(rows[0].id) if rows else None}

def _target_progress(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    rows = list(db.execute(select(SustainabilityTarget).where(SustainabilityTarget.organization_id == organization_id).order_by(SustainabilityTarget.updated_at.desc()).limit(5)).scalars())
    parts = []
    for t in rows:
        parts.append(f'{t.name} status={t.status}')
    return {'summary': 'Targets: ' + ('; '.join(parts) if parts else 'none'), 'recordId': str(rows[0].id) if rows else None}

def _sustainability_summary(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    inv = _summarize_inventory(db, organization_id, question)
    targets = _target_progress(db, organization_id, question)
    passport = _summarize_passport(db, organization_id, question)
    return {'summary': f"{inv['summary']} | {targets['summary']} | {passport['summary']}", 'recordId': inv.get('recordId')}

def _find_related_documents(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    from ecotrace.modules.knowledge.infrastructure.models import KnowledgeDocument
    tokens = [t for t in re.findall('[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}', question.lower())][:5]
    stmt = select(KnowledgeDocument).where(KnowledgeDocument.organization_id == organization_id, KnowledgeDocument.status == 'published')
    docs = list(db.execute(stmt.limit(20)).scalars())
    scored: list[tuple[int, KnowledgeDocument]] = []
    for doc in docs:
        blob = f"{doc.title} {' '.join(doc.tags or [])}".lower()
        score = sum((1 for t in tokens if t in blob))
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]
    summary = '; '.join((f'{d.title} ({d.document_type})' for _, d in top)) or 'No related documents'
    return {'summary': summary, 'recordId': str(top[0][1].id) if top else None}

def _locate_evidence(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    return _find_related_documents(db, organization_id, question)

def _compare_inventories(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    _ = question
    rows = list(db.execute(select(CarbonInventory).where(CarbonInventory.organization_id == organization_id).order_by(CarbonInventory.updated_at.desc()).limit(2)).scalars())
    if len(rows) < 2:
        return {'summary': 'Need at least two inventories to compare.', 'recordId': None}
    a, b = (rows[0], rows[1])
    return {'summary': f"Comparing '{a.name}' ({a.status}) vs '{b.name}' ({b.status}).", 'recordId': str(a.id)}

def _explain_increase(db: Session, organization_id: uuid.UUID, question: str) -> dict[str, Any]:
    return _compare_inventories(db, organization_id, question)
_HANDLERS = {'summarize_inventory': _summarize_inventory, 'compare_inventories': _compare_inventories, 'explain_emission_increase': _explain_increase, 'highest_emitting_facility': _highest_facility, 'explain_scope_breakdown': _scope_breakdown, 'summarize_product_footprint': _summarize_product_footprint, 'summarize_passport': _summarize_passport, 'compare_products': _compare_products, 'compare_scenarios': _compare_scenarios, 'explain_target_progress': _target_progress, 'generate_sustainability_summary': _sustainability_summary, 'find_related_documents': _find_related_documents, 'locate_evidence': _locate_evidence}
