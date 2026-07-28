from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.anomaly_detection.application.detectors import fingerprint
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import DataQualityIssue
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_read, require_automation_write

def scan(db: Session, user: User, organization_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    created = 0
    checks: list[tuple[str, str, str, str]] = []
    from ecotrace.modules.data_imports.infrastructure.models import ImportJob
    from ecotrace.modules.facilities.infrastructure.models import Facility
    from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
    facility_count = db.execute(select(func.count()).select_from(Facility).where(Facility.organization_id == organization_id)).scalar_one()
    if facility_count == 0:
        checks.append(('incomplete_facility_data', 'organization', 'Missing facilities', 'high'))
    period_count = db.execute(select(func.count()).select_from(ReportingPeriod).where(ReportingPeriod.organization_id == organization_id)).scalar_one()
    if period_count == 0:
        checks.append(('missing_reporting_periods', 'organization', 'Missing reporting periods', 'medium'))
    failed_imports = db.execute(select(func.count()).select_from(ImportJob).where(ImportJob.organization_id == organization_id, ImportJob.status.in_(['failed', 'error']))).scalar_one()
    if failed_imports:
        checks.append(('failed_imports', 'data_import', f'{failed_imports} failed import job(s)', 'high'))
    from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
    backlog = db.execute(select(func.count()).select_from(ActivityRecord).where(ActivityRecord.organization_id == organization_id, ActivityRecord.status.in_(['draft', 'submitted']))).scalar_one()
    if backlog > 20:
        checks.append(('unapproved_activity_backlog', 'activity_record', f'Unapproved activity backlog: {backlog}', 'medium'))
    for issue_type, entity_type, title, severity in checks:
        fp = fingerprint(organization_id, issue_type, entity_type, title)
        exists = db.execute(select(DataQualityIssue.id).where(DataQualityIssue.organization_id == organization_id, DataQualityIssue.fingerprint == fp)).scalar_one_or_none()
        if exists:
            continue
        db.add(DataQualityIssue(organization_id=organization_id, fingerprint=fp, issue_type=issue_type, entity_type=entity_type, entity_id=None, severity=severity, title=title, description=title, evidence_json={'detectedBy': 'phase7-data-quality-scan'}, status='open', detected_at=datetime.now(UTC)))
        created += 1
    write_audit_log(db, action='data_quality.scan.completed', actor_user_id=user.id, organization_id=organization_id, entity_type='organization', entity_id=str(organization_id), metadata={'created': created})
    db.flush()
    return {'created': created, 'checked': len(checks)}

def list_issues(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(DataQualityIssue).where(DataQualityIssue.organization_id == organization_id).order_by(DataQualityIssue.detected_at.desc())).scalars()
    return [_ser(r) for r in rows]

def get_issue(db: Session, user: User, organization_id: uuid.UUID, issue_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser(_get(db, organization_id, issue_id))

def assign(db: Session, user: User, organization_id: uuid.UUID, issue_id: uuid.UUID, assignee_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, issue_id)
    row.assigned_to_user_id = assignee_id
    db.flush()
    return _ser(row)

def resolve(db: Session, user: User, organization_id: uuid.UUID, issue_id: uuid.UUID, notes: str | None) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, issue_id)
    row.status = 'resolved'
    row.resolved_at = datetime.now(UTC)
    row.resolution_notes = notes
    write_audit_log(db, action='data_quality.issue.resolved', actor_user_id=user.id, organization_id=organization_id, entity_type='data_quality_issue', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def dismiss(db: Session, user: User, organization_id: uuid.UUID, issue_id: uuid.UUID, reason: str) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    if not reason.strip():
        raise ValidationAppError('Dismissal reason required.')
    row = _get(db, organization_id, issue_id)
    row.status = 'dismissed'
    row.resolved_at = datetime.now(UTC)
    row.resolution_notes = reason
    db.flush()
    return _ser(row)

def _get(db: Session, organization_id: uuid.UUID, issue_id: uuid.UUID) -> DataQualityIssue:
    row = db.execute(select(DataQualityIssue).where(DataQualityIssue.id == issue_id, DataQualityIssue.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Data quality issue not found.')
    return row

def _ser(row: DataQualityIssue) -> dict[str, Any]:
    return {'id': str(row.id), 'issueType': row.issue_type, 'entityType': row.entity_type, 'entityId': str(row.entity_id) if row.entity_id else None, 'severity': row.severity, 'title': row.title, 'description': row.description, 'evidence': row.evidence_json, 'status': row.status, 'detectedAt': row.detected_at.isoformat() if row.detected_at else None, 'assignedToUserId': str(row.assigned_to_user_id) if row.assigned_to_user_id else None, 'dueDate': row.due_date.isoformat() if row.due_date else None, 'resolutionNotes': row.resolution_notes}
