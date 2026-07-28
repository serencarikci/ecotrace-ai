from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError
from ecotrace.modules.anomaly_detection.application.detectors import fingerprint
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import Alert
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_read, require_automation_write

def create_alert(db: Session, organization_id: uuid.UUID, *, alert_type: str, source_type: str, source_id: uuid.UUID | None, title: str, message: str, severity: str='medium', evidence: dict[str, Any] | None=None) -> dict[str, Any]:
    fp = fingerprint(organization_id, alert_type, source_type, source_id, title)
    existing = db.execute(select(Alert).where(Alert.organization_id == organization_id, Alert.fingerprint == fp)).scalar_one_or_none()
    if existing:
        return _ser(existing)
    row = Alert(organization_id=organization_id, fingerprint=fp, alert_type=alert_type, source_type=source_type, source_id=source_id, title=title, message=message, severity=severity, status='open', evidence_json=evidence, created_by_system=True)
    db.add(row)
    db.flush()
    return _ser(row)

def list_alerts(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(Alert).where(Alert.organization_id == organization_id).order_by(Alert.created_at.desc()).limit(200)).scalars()
    return [_ser(r) for r in rows]

def get_alert(db: Session, user: User, organization_id: uuid.UUID, alert_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser(_get(db, organization_id, alert_id))

def acknowledge(db: Session, user: User, organization_id: uuid.UUID, alert_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, alert_id)
    row.status = 'acknowledged'
    row.acknowledged_at = datetime.now(UTC)
    write_audit_log(db, action='alert.acknowledged', actor_user_id=user.id, organization_id=organization_id, entity_type='alert', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def assign(db: Session, user: User, organization_id: uuid.UUID, alert_id: uuid.UUID, assignee_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, alert_id)
    row.assigned_to_user_id = assignee_id
    write_audit_log(db, action='alert.assigned', actor_user_id=user.id, organization_id=organization_id, entity_type='alert', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def resolve(db: Session, user: User, organization_id: uuid.UUID, alert_id: uuid.UUID, notes: str | None) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, alert_id)
    row.status = 'resolved'
    row.resolved_at = datetime.now(UTC)
    row.resolution_notes = notes
    write_audit_log(db, action='alert.resolved', actor_user_id=user.id, organization_id=organization_id, entity_type='alert', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def _get(db: Session, organization_id: uuid.UUID, alert_id: uuid.UUID) -> Alert:
    row = db.execute(select(Alert).where(Alert.id == alert_id, Alert.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Alert not found.')
    return row

def _ser(row: Alert) -> dict[str, Any]:
    return {'id': str(row.id), 'alertType': row.alert_type, 'sourceType': row.source_type, 'sourceId': str(row.source_id) if row.source_id else None, 'title': row.title, 'message': row.message, 'severity': row.severity, 'status': row.status, 'evidence': row.evidence_json, 'assignedToUserId': str(row.assigned_to_user_id) if row.assigned_to_user_id else None, 'createdAt': row.created_at.isoformat() if row.created_at else None}
