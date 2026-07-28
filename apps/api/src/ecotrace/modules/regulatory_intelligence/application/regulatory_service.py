from __future__ import annotations
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import OrganizationRegulatoryAssessment, RegulatoryDocument
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_read, require_automation_write, require_system_admin
LEGAL_DISCLAIMER = 'This module provides document intelligence and internal decision support. It does not provide legal advice or guarantee regulatory compliance.'

def list_documents(db: Session, user: User) -> list[dict[str, Any]]:
    _ = user
    rows = db.execute(select(RegulatoryDocument).order_by(RegulatoryDocument.updated_at.desc())).scalars()
    return [_ser_doc(r) for r in rows]

def create_document(db: Session, user: User, payload: dict[str, Any]) -> dict[str, Any]:
    require_system_admin(user)
    row = RegulatoryDocument(jurisdiction_code=str(payload['jurisdictionCode']), authority_name=str(payload['authorityName']), regulation_code=str(payload['regulationCode']), title=str(payload['title']), description=payload.get('description'), category=str(payload.get('category') or 'climate'), source_url=payload.get('sourceUrl'), published_at=_parse_date(payload.get('publishedAt')), effective_from=_parse_date(payload.get('effectiveFrom')), effective_to=_parse_date(payload.get('effectiveTo')), version=str(payload.get('version') or '1'), status=str(payload.get('status') or 'active'), is_demo=bool(payload.get('isDemo', True)), applicability_tags_json=payload.get('applicabilityTags') or [])
    db.add(row)
    db.flush()
    write_audit_log(db, action='regulatory.document.created', actor_user_id=user.id, entity_type='regulatory_document', entity_id=str(row.id))
    return _ser_doc(row)

def get_document(db: Session, user: User, document_id: uuid.UUID) -> dict[str, Any]:
    _ = user
    row = db.get(RegulatoryDocument, document_id)
    if row is None:
        raise NotFoundError('Regulatory document not found.')
    return _ser_doc(row)

def update_document(db: Session, user: User, document_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_system_admin(user)
    row = db.get(RegulatoryDocument, document_id)
    if row is None:
        raise NotFoundError('Regulatory document not found.')
    for key, attr in {'title': 'title', 'description': 'description', 'status': 'status', 'category': 'category', 'sourceUrl': 'source_url'}.items():
        if key in payload:
            setattr(row, attr, payload[key])
    db.flush()
    return _ser_doc(row)

def list_assessments(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(OrganizationRegulatoryAssessment).where(OrganizationRegulatoryAssessment.organization_id == organization_id)).scalars()
    return [_ser_assessment(r) for r in rows]

def get_assessment(db: Session, user: User, organization_id: uuid.UUID, assessment_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser_assessment(_get_assessment(db, organization_id, assessment_id))

def update_assessment(db: Session, user: User, organization_id: uuid.UUID, assessment_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_assessment(db, organization_id, assessment_id)
    for key, attr in {'applicabilityStatus': 'applicability_status', 'assessmentNotes': 'assessment_notes', 'impactSummary': 'impact_summary', 'actionRequired': 'action_required', 'dueDate': 'due_date', 'assignedToUserId': 'assigned_to_user_id'}.items():
        if key in payload:
            val = payload[key]
            if key == 'dueDate' and val:
                val = _parse_date(val)
            if key == 'assignedToUserId' and val:
                val = uuid.UUID(str(val))
            setattr(row, attr, val)
    db.flush()
    return _ser_assessment(row)

def review_assessment(db: Session, user: User, organization_id: uuid.UUID, assessment_id: uuid.UUID, *, applicability_status: str, notes: str | None=None) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    if applicability_status not in {'applicable', 'potentially_applicable', 'not_applicable', 'unknown'}:
        raise ValidationAppError('Invalid applicability status.')
    row = _get_assessment(db, organization_id, assessment_id)
    row.applicability_status = applicability_status
    row.review_status = 'reviewed'
    row.assessment_notes = notes
    row.reviewed_at = datetime.now(UTC)
    write_audit_log(db, action='regulatory.assessment.reviewed', actor_user_id=user.id, organization_id=organization_id, entity_type='organization_regulatory_assessment', entity_id=str(row.id))
    db.flush()
    return _ser_assessment(row)

def scan_org(db: Session, user: User, organization_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    docs = list(db.execute(select(RegulatoryDocument).where(RegulatoryDocument.status == 'active')).scalars())
    created = 0
    for doc in docs:
        existing = db.execute(select(OrganizationRegulatoryAssessment).where(OrganizationRegulatoryAssessment.organization_id == organization_id, OrganizationRegulatoryAssessment.regulatory_document_id == doc.id)).scalar_one_or_none()
        if existing:
            continue
        upcoming = bool(doc.effective_from and doc.effective_from <= date.today() + timedelta(days=90))
        row = OrganizationRegulatoryAssessment(organization_id=organization_id, regulatory_document_id=doc.id, applicability_status='unknown', relevance_score=Decimal('0.5'), review_status='pending', impact_summary='AI-assisted classification requires human review.', action_required=upcoming, due_date=doc.effective_from, citations_json=[{'label': 'R1', 'documentName': doc.title, 'recordId': str(doc.id), 'databaseSource': 'regulatory_document'}])
        db.add(row)
        created += 1
        if upcoming:
            from ecotrace.modules.alerts.application import alert_service
            alert_service.create_alert(db, organization_id, alert_type='document_expiration', source_type='regulatory_document', source_id=doc.id, title=f'Upcoming regulatory effective date: {doc.regulation_code}', message=f'{doc.title} may become effective soon.', severity='medium')
    db.flush()
    return {'created': created, 'disclaimer': LEGAL_DISCLAIMER}

def _get_assessment(db: Session, organization_id: uuid.UUID, assessment_id: uuid.UUID) -> OrganizationRegulatoryAssessment:
    row = db.execute(select(OrganizationRegulatoryAssessment).where(OrganizationRegulatoryAssessment.id == assessment_id, OrganizationRegulatoryAssessment.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Regulatory assessment not found.')
    return row

def _parse_date(value: object) -> date | None:
    if value is None or value == '':
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])

def _ser_doc(row: RegulatoryDocument) -> dict[str, Any]:
    return {'id': str(row.id), 'jurisdictionCode': row.jurisdiction_code, 'authorityName': row.authority_name, 'regulationCode': row.regulation_code, 'title': row.title, 'description': row.description, 'category': row.category, 'sourceUrl': row.source_url, 'publishedAt': row.published_at.isoformat() if row.published_at else None, 'effectiveFrom': row.effective_from.isoformat() if row.effective_from else None, 'effectiveTo': row.effective_to.isoformat() if row.effective_to else None, 'version': row.version, 'status': row.status, 'isDemo': row.is_demo, 'disclaimer': LEGAL_DISCLAIMER}

def _ser_assessment(row: OrganizationRegulatoryAssessment) -> dict[str, Any]:
    return {'id': str(row.id), 'regulatoryDocumentId': str(row.regulatory_document_id), 'applicabilityStatus': row.applicability_status, 'relevanceScore': float(row.relevance_score) if row.relevance_score is not None else None, 'reviewStatus': row.review_status, 'assessmentNotes': row.assessment_notes, 'impactSummary': row.impact_summary, 'actionRequired': row.action_required, 'dueDate': row.due_date.isoformat() if row.due_date else None, 'reviewedAt': row.reviewed_at.isoformat() if row.reviewed_at else None, 'citations': row.citations_json or [], 'disclaimer': LEGAL_DISCLAIMER}
