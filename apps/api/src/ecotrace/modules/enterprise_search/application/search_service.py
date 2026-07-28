from __future__ import annotations
import uuid
from typing import Any, cast
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonInventory
from ecotrace.modules.digital_product_passport.infrastructure.models import DigitalProductPassport
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.knowledge.infrastructure.models import KnowledgeDocument, SavedSearch
from ecotrace.modules.products.infrastructure.models import Product
from ecotrace.modules.retrieval.application.hybrid_search import hybrid_retrieve
from ecotrace.modules.scenarios.infrastructure.models import ScenarioModel
from ecotrace.modules.sustainability_targets.infrastructure.models import SustainabilityTarget
from ecotrace.shared.application.org_access import require_ai_read, require_ai_write

def enterprise_search(db: Session, user: User, organization_id: uuid.UUID, *, query: str, mode: str='hybrid', document_type: str | None=None, language: str | None=None, limit: int=20) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    q = query.strip()
    facets: dict[str, Any] = {'sources': {}, 'documentTypes': {}}
    results: list[dict[str, Any]] = []
    if mode in {'semantic', 'hybrid', 'full-text'}:
        evidence, metrics = hybrid_retrieve(db, user, organization_id, query=q, top_k=limit, document_type=document_type, language=language)
        for item in evidence:
            results.append({'id': item.chunk_id, 'source': 'document', 'title': item.document_title, 'snippet': item.content[:280], 'score': item.score, 'documentType': item.document_type, 'recordId': item.document_id})
            facets['sources']['document'] = facets['sources'].get('document', 0) + 1
            facets['documentTypes'][item.document_type] = facets['documentTypes'].get(item.document_type, 0) + 1
        retrieval_metrics = metrics
    else:
        retrieval_metrics = {}
    like = f'%{q}%'
    for model, source, title_attr in ((Product, 'product', 'name'), (CarbonInventory, 'carbon_inventory', 'name'), (DigitalProductPassport, 'passport', 'title'), (SustainabilityTarget, 'target', 'name'), (ScenarioModel, 'scenario', 'name'), (KnowledgeDocument, 'knowledge_document', 'title')):
        stmt = select(model).where(model.organization_id == organization_id).where(getattr(model, title_attr).ilike(like)).limit(5)
        if source == 'knowledge_document':
            stmt = stmt.where(KnowledgeDocument.status == 'published')
        rows = list(db.execute(stmt).scalars())
        for row in rows:
            entity = cast(Any, row)
            row_id = str(entity.id)
            title = str(getattr(entity, title_attr))
            results.append({'id': row_id, 'source': source, 'title': title, 'snippet': title, 'score': 0.5, 'documentType': source, 'recordId': row_id})
            facets['sources'][source] = facets['sources'].get(source, 0) + 1
    results.sort(key=lambda r: r['score'], reverse=True)
    return {'query': q, 'mode': mode, 'items': results[:limit], 'facets': facets, 'metrics': retrieval_metrics}

def autocomplete(db: Session, user: User, organization_id: uuid.UUID, *, prefix: str, limit: int=10) -> list[dict[str, str]]:
    require_ai_read(db, user, organization_id)
    if len(prefix.strip()) < 2:
        return []
    like = f'{prefix.strip()}%'
    suggestions: list[dict[str, str]] = []
    docs = db.execute(select(KnowledgeDocument.title).where(KnowledgeDocument.organization_id == organization_id, KnowledgeDocument.status == 'published', KnowledgeDocument.title.ilike(like)).limit(limit)).scalars()
    for title in docs:
        suggestions.append({'text': title, 'source': 'document'})
    products = db.execute(select(Product.name).where(Product.organization_id == organization_id, Product.name.ilike(like)).limit(limit)).scalars()
    for name in products:
        suggestions.append({'text': name, 'source': 'product'})
    return suggestions[:limit]

def save_search(db: Session, user: User, organization_id: uuid.UUID, *, name: str, query_text: str, filters: dict[str, Any] | None=None, search_mode: str='hybrid') -> dict[str, Any]:
    require_ai_write(db, user, organization_id)
    row = SavedSearch(organization_id=organization_id, owner_user_id=user.id, name=name.strip()[:255], query_text=query_text, filters_json=filters or {}, search_mode=search_mode)
    db.add(row)
    db.flush()
    return {'id': str(row.id), 'name': row.name, 'queryText': row.query_text, 'searchMode': row.search_mode}

def list_saved_searches(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    rows = db.execute(select(SavedSearch).where(SavedSearch.organization_id == organization_id, SavedSearch.owner_user_id == user.id)).scalars()
    return [{'id': str(r.id), 'name': r.name, 'queryText': r.query_text, 'filters': r.filters_json or {}, 'searchMode': r.search_mode} for r in rows]

def conversation_analytics(db: Session, user: User, organization_id: uuid.UUID) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    from ecotrace.modules.knowledge.infrastructure.models import ChatConversation, ChatMessage, RetrievalLog
    conversations = db.execute(select(func.count()).select_from(ChatConversation).where(ChatConversation.organization_id == organization_id, ChatConversation.status != 'deleted')).scalar_one()
    messages = db.execute(select(func.count()).select_from(ChatMessage).where(ChatMessage.organization_id == organization_id)).scalar_one()
    avg_latency = db.execute(select(func.avg(RetrievalLog.llm_latency_ms)).where(RetrievalLog.organization_id == organization_id)).scalar()
    cache_hits = db.execute(select(func.count()).select_from(RetrievalLog).where(RetrievalLog.organization_id == organization_id, RetrievalLog.cache_hit.is_(True))).scalar_one()
    total_logs = db.execute(select(func.count()).select_from(RetrievalLog).where(RetrievalLog.organization_id == organization_id)).scalar_one()
    return {'conversations': conversations, 'messages': messages, 'avgLlmLatencyMs': float(avg_latency or 0), 'cacheHitRate': cache_hits / total_logs if total_logs else 0.0, 'retrievalLogs': total_logs}
