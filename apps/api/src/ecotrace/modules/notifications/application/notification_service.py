from __future__ import annotations
import uuid
from datetime import UTC, datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import OrganizationMembership
from ecotrace.modules.production_operations.infrastructure.models import Notification, NotificationPreference
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_read, require_automation_write

def notify_user(db: Session, *, user_id: uuid.UUID, organization_id: uuid.UUID, title: str, message: str, notification_type: str, severity: str='info', action_url: str | None=None) -> dict[str, Any]:
    row = Notification(user_id=user_id, organization_id=organization_id, notification_type=notification_type, title=title, message=message, action_url=action_url, severity=severity, status='sent', sent_at=datetime.now(UTC))
    db.add(row)
    db.flush()
    return _ser(row)

def notify_org_admins(db: Session, organization_id: uuid.UUID, *, title: str, message: str, notification_type: str) -> dict[str, Any]:
    memberships = db.execute(select(OrganizationMembership).where(OrganizationMembership.organization_id == organization_id, OrganizationMembership.is_active.is_(True))).scalars()
    created = 0
    for m in memberships:
        notify_user(db, user_id=m.user_id, organization_id=organization_id, title=title, message=message, notification_type=notification_type)
        created += 1
    return {'created': created}

def list_notifications(db: Session, user: User) -> list[dict[str, Any]]:
    rows = db.execute(select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(200)).scalars()
    return [_ser(r) for r in rows]

def unread_count(db: Session, user: User) -> dict[str, int]:
    count = db.execute(select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))).scalar_one()
    return {'count': count}

def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> dict[str, Any]:
    row = db.execute(select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Notification not found.')
    row.read_at = datetime.now(UTC)
    row.status = 'read'
    db.flush()
    return _ser(row)

def mark_all_read(db: Session, user: User) -> dict[str, int]:
    rows = db.execute(select(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))).scalars()
    n = 0
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
        row.status = 'read'
        n += 1
    db.flush()
    return {'updated': n}

def get_preferences(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id, NotificationPreference.organization_id == organization_id)).scalars()
    items = [_ser_pref(r) for r in rows]
    if not items:
        pref = NotificationPreference(user_id=user.id, organization_id=organization_id, notification_type='default', in_app_enabled=True, email_enabled=False, minimum_severity='low', digest_frequency='realtime', timezone='UTC')
        db.add(pref)
        db.flush()
        items = [_ser_pref(pref)]
    return items

def update_preferences(db: Session, user: User, organization_id: uuid.UUID, payload: dict[str, Any]) -> list[dict[str, Any]]:
    require_automation_write(db, user, organization_id)
    prefs = get_preferences(db, user, organization_id)
    row = db.execute(select(NotificationPreference).where(NotificationPreference.user_id == user.id, NotificationPreference.organization_id == organization_id, NotificationPreference.notification_type == str(payload.get('notificationType') or 'default'))).scalar_one_or_none()
    if row is None:
        row = NotificationPreference(user_id=user.id, organization_id=organization_id, notification_type=str(payload.get('notificationType') or 'default'))
        db.add(row)
    for key, attr in {'inAppEnabled': 'in_app_enabled', 'emailEnabled': 'email_enabled', 'minimumSeverity': 'minimum_severity', 'digestFrequency': 'digest_frequency', 'quietHoursStart': 'quiet_hours_start', 'quietHoursEnd': 'quiet_hours_end', 'timezone': 'timezone'}.items():
        if key in payload:
            setattr(row, attr, payload[key])
    write_audit_log(db, action='notification.preference.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='notification_preference', entity_id=str(row.id))
    db.flush()
    _ = prefs
    return get_preferences(db, user, organization_id)

def _ser(row: Notification) -> dict[str, Any]:
    return {'id': str(row.id), 'organizationId': str(row.organization_id), 'notificationType': row.notification_type, 'title': row.title, 'message': row.message, 'actionUrl': row.action_url, 'severity': row.severity, 'status': row.status, 'readAt': row.read_at.isoformat() if row.read_at else None, 'createdAt': row.created_at.isoformat() if row.created_at else None}

def _ser_pref(row: NotificationPreference) -> dict[str, Any]:
    return {'id': str(row.id), 'notificationType': row.notification_type, 'inAppEnabled': row.in_app_enabled, 'emailEnabled': row.email_enabled, 'minimumSeverity': row.minimum_severity, 'digestFrequency': row.digest_frequency, 'quietHoursStart': row.quiet_hours_start, 'quietHoursEnd': row.quiet_hours_end, 'timezone': row.timezone}
