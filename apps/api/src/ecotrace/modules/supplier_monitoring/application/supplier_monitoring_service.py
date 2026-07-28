from __future__ import annotations
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import SupplierAssessment, SupplierMonitoringProfile
from ecotrace.modules.suppliers.infrastructure.models import Supplier
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_read, require_automation_write

def list_profiles(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(SupplierMonitoringProfile).where(SupplierMonitoringProfile.organization_id == organization_id)).scalars()
    return [_ser_profile(r) for r in rows]

def get_profile(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    row = _get_or_create(db, organization_id, supplier_id)
    return _ser_profile(row)

def update_profile(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_or_create(db, organization_id, supplier_id)
    for key, attr in {'monitoringStatus': 'monitoring_status', 'riskLevel': 'risk_level', 'reviewFrequency': 'review_frequency', 'requiredDocumentTypes': 'required_document_types_json', 'assignedToUserId': 'assigned_to_user_id'}.items():
        if key in payload:
            val = payload[key]
            if key == 'assignedToUserId' and val:
                val = uuid.UUID(str(val))
            setattr(row, attr, val)
    db.flush()
    return _ser_profile(row)

def assess(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    profile = _get_or_create(db, organization_id, supplier_id)
    doc_score = Decimal('0.70')
    dq_score = Decimal('0.75')
    emissions_score = Decimal('0.65')
    overall = (doc_score + dq_score + emissions_score) / Decimal('3')
    risk = 'low' if overall >= Decimal('0.8') else 'medium' if overall >= Decimal('0.6') else 'high'
    overdue = bool(profile.next_review_at and profile.next_review_at < datetime.now(UTC))
    assessment = SupplierAssessment(organization_id=organization_id, supplier_id=supplier_id, assessment_date=date.today(), assessment_type='internal', emissions_score=emissions_score, data_quality_score=dq_score, document_completeness_score=doc_score, sustainability_score=overall, risk_level=risk, findings_json={'overdueReview': overdue, 'note': 'Internal non-certified assessment.'}, recommendations_json={'actions': ['Request latest sustainability questionnaire']}, assessed_by_user_id=user.id, status='completed')
    db.add(assessment)
    profile.last_reviewed_at = datetime.now(UTC)
    profile.next_review_at = datetime.now(UTC) + timedelta(days=90)
    profile.risk_level = risk
    write_audit_log(db, action='supplier.assessment.completed', actor_user_id=user.id, organization_id=organization_id, entity_type='supplier_assessment', entity_id=str(assessment.id))
    if overdue:
        from ecotrace.modules.alerts.application import alert_service
        alert_service.create_alert(db, organization_id, alert_type='supplier_issue', source_type='supplier', source_id=supplier_id, title='Supplier review overdue', message='Supplier monitoring review is overdue.', severity='medium')
    db.flush()
    return _ser_assessment(assessment)

def list_assessments(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(SupplierAssessment).where(SupplierAssessment.organization_id == organization_id, SupplierAssessment.supplier_id == supplier_id).order_by(SupplierAssessment.assessment_date.desc())).scalars()
    return [_ser_assessment(r) for r in rows]

def _get_or_create(db: Session, organization_id: uuid.UUID, supplier_id: uuid.UUID) -> SupplierMonitoringProfile:
    supplier = db.execute(select(Supplier).where(Supplier.id == supplier_id, Supplier.organization_id == organization_id)).scalar_one_or_none()
    if supplier is None:
        raise NotFoundError('Supplier not found.')
    row = db.execute(select(SupplierMonitoringProfile).where(SupplierMonitoringProfile.organization_id == organization_id, SupplierMonitoringProfile.supplier_id == supplier_id)).scalar_one_or_none()
    if row:
        return row
    row = SupplierMonitoringProfile(organization_id=organization_id, supplier_id=supplier_id, monitoring_status='active', risk_level='medium', required_document_types_json=['certificate', 'policy'], review_frequency='quarterly', next_review_at=datetime.now(UTC) - timedelta(days=1))
    db.add(row)
    db.flush()
    return row

def _ser_profile(row: SupplierMonitoringProfile) -> dict[str, Any]:
    return {'id': str(row.id), 'supplierId': str(row.supplier_id), 'monitoringStatus': row.monitoring_status, 'riskLevel': row.risk_level, 'requiredDocumentTypes': row.required_document_types_json or [], 'reviewFrequency': row.review_frequency, 'lastReviewedAt': row.last_reviewed_at.isoformat() if row.last_reviewed_at else None, 'nextReviewAt': row.next_review_at.isoformat() if row.next_review_at else None, 'assignedToUserId': str(row.assigned_to_user_id) if row.assigned_to_user_id else None, 'disclaimer': 'Internal non-certified monitoring scores.', 'overdue': bool(row.next_review_at and row.next_review_at < datetime.now(UTC))}

def _ser_assessment(row: SupplierAssessment) -> dict[str, Any]:
    return {'id': str(row.id), 'supplierId': str(row.supplier_id), 'assessmentDate': row.assessment_date.isoformat(), 'assessmentType': row.assessment_type, 'emissionsScore': float(row.emissions_score) if row.emissions_score is not None else None, 'dataQualityScore': float(row.data_quality_score) if row.data_quality_score is not None else None, 'documentCompletenessScore': float(row.document_completeness_score) if row.document_completeness_score is not None else None, 'sustainabilityScore': float(row.sustainability_score) if row.sustainability_score is not None else None, 'riskLevel': row.risk_level, 'findings': row.findings_json, 'recommendations': row.recommendations_json, 'status': row.status, 'disclaimer': row.disclaimer}
