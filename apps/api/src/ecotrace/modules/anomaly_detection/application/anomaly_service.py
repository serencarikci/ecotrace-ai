from __future__ import annotations
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import NotFoundError, ValidationAppError
from ecotrace.modules.anomaly_detection.application.detectors import fingerprint, percentage_change, severity_from_score, z_score
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import AnomalyDetectionRule, AnomalyEvent
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_manage, require_automation_read, require_automation_write

def list_rules(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(AnomalyDetectionRule).where(AnomalyDetectionRule.organization_id == organization_id)).scalars()
    return [_ser_rule(r) for r in rows]

def create_rule(db: Session, user: User, organization_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = AnomalyDetectionRule(organization_id=organization_id, code=str(payload['code']), name=str(payload['name']), description=payload.get('description'), metric_type=str(payload.get('metricType') or 'activity_quantity'), detection_method=str(payload.get('detectionMethod') or 'z_score'), threshold_config_json=payload.get('thresholdConfig') or {'z': 3.0, 'pct': 50.0}, scope_config_json=payload.get('scopeConfig') or {}, severity_mapping_json=payload.get('severityMapping') or {}, minimum_data_points=int(payload.get('minimumDataPoints') or 5), lookback_period=int(payload.get('lookbackPeriod') or 12), is_active=True)
    db.add(row)
    db.flush()
    write_audit_log(db, action='anomaly.rule.created', actor_user_id=user.id, organization_id=organization_id, entity_type='anomaly_detection_rule', entity_id=str(row.id))
    return _ser_rule(row)

def update_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = db.execute(select(AnomalyDetectionRule).where(AnomalyDetectionRule.id == rule_id, AnomalyDetectionRule.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Anomaly rule not found.')
    if 'name' in payload:
        row.name = payload['name']
    if 'isActive' in payload:
        row.is_active = bool(payload['isActive'])
    if 'thresholdConfig' in payload:
        row.threshold_config_json = payload['thresholdConfig']
    db.flush()
    return _ser_rule(row)

def run_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    rule = db.execute(select(AnomalyDetectionRule).where(AnomalyDetectionRule.id == rule_id, AnomalyDetectionRule.organization_id == organization_id)).scalar_one_or_none()
    if rule is None:
        raise NotFoundError('Anomaly rule not found.')
    return _detect_for_rule(db, user, organization_id, rule)

def run_org_scan(db: Session, user: User, organization_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    rules = list(db.execute(select(AnomalyDetectionRule).where(AnomalyDetectionRule.organization_id == organization_id, AnomalyDetectionRule.is_active.is_(True))).scalars())
    created = 0
    for rule in rules:
        result = _detect_for_rule(db, user, organization_id, rule)
        created += int(result.get('created') or 0)
    if not rules:
        created += _default_activity_scan(db, user, organization_id)
    return {'created': created, 'rulesScanned': len(rules)}

def list_anomalies(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(AnomalyEvent).where(AnomalyEvent.organization_id == organization_id).order_by(AnomalyEvent.detected_at.desc()).limit(200)).scalars()
    return [_ser_event(r) for r in rows]

def get_anomaly(db: Session, user: User, organization_id: uuid.UUID, anomaly_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser_event(_get_event(db, organization_id, anomaly_id))

def acknowledge(db: Session, user: User, organization_id: uuid.UUID, anomaly_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_event(db, organization_id, anomaly_id)
    row.status = 'acknowledged'
    row.acknowledged_at = datetime.now(UTC)
    write_audit_log(db, action='anomaly.acknowledged', actor_user_id=user.id, organization_id=organization_id, entity_type='anomaly_event', entity_id=str(row.id))
    db.flush()
    return _ser_event(row)

def assign(db: Session, user: User, organization_id: uuid.UUID, anomaly_id: uuid.UUID, assignee_id: uuid.UUID) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_event(db, organization_id, anomaly_id)
    row.assigned_to_user_id = assignee_id
    row.status = 'investigating'
    write_audit_log(db, action='anomaly.assigned', actor_user_id=user.id, organization_id=organization_id, entity_type='anomaly_event', entity_id=str(row.id))
    db.flush()
    return _ser_event(row)

def resolve(db: Session, user: User, organization_id: uuid.UUID, anomaly_id: uuid.UUID, notes: str | None) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get_event(db, organization_id, anomaly_id)
    row.status = 'resolved'
    row.resolved_at = datetime.now(UTC)
    row.resolution_notes = notes
    write_audit_log(db, action='anomaly.resolved', actor_user_id=user.id, organization_id=organization_id, entity_type='anomaly_event', entity_id=str(row.id))
    db.flush()
    return _ser_event(row)

def dismiss(db: Session, user: User, organization_id: uuid.UUID, anomaly_id: uuid.UUID, reason: str) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    if not reason.strip():
        raise ValidationAppError('Dismissal requires a reason.')
    row = _get_event(db, organization_id, anomaly_id)
    row.status = 'dismissed'
    row.resolved_at = datetime.now(UTC)
    row.resolution_notes = reason
    write_audit_log(db, action='anomaly.dismissed', actor_user_id=user.id, organization_id=organization_id, entity_type='anomaly_event', entity_id=str(row.id))
    db.flush()
    return _ser_event(row)

def _detect_for_rule(db: Session, user: User, organization_id: uuid.UUID, rule: AnomalyDetectionRule) -> dict[str, Any]:
    _ = user
    from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
    rows = list(db.execute(select(ActivityRecord).where(ActivityRecord.organization_id == organization_id).order_by(ActivityRecord.created_at.desc()).limit(max(rule.lookback_period, 12))).scalars())
    values = [float(r.quantity) for r in rows if getattr(r, 'quantity', None) is not None]
    if len(values) < rule.minimum_data_points:
        return {'created': 0, 'reason': 'insufficient_data'}
    observed = values[0]
    history = values[1:]
    score = z_score(history, observed) or 0.0
    pct = percentage_change(history[0], observed) if history else None
    thr = float((rule.threshold_config_json or {}).get('z') or 3.0)
    if abs(score) < thr and (pct is None or abs(pct) < float((rule.threshold_config_json or {}).get('pct') or 50)):
        return {'created': 0}
    fp = fingerprint(organization_id, rule.code, 'activity', round(observed, 4), datetime.now(UTC).date())
    existing = db.execute(select(AnomalyEvent).where(AnomalyEvent.organization_id == organization_id, AnomalyEvent.fingerprint == fp)).scalar_one_or_none()
    if existing:
        return {'created': 0, 'deduped': True}
    expected = sum(history) / len(history) if history else observed
    event = AnomalyEvent(organization_id=organization_id, rule_id=rule.id, fingerprint=fp, entity_type='activity_record', entity_id=rows[0].id if rows else None, metric_code=rule.metric_type, observed_value=Decimal(str(observed)), expected_value=Decimal(str(round(expected, 8))), deviation_value=Decimal(str(round(observed - expected, 8))), deviation_percentage=Decimal(str(round(pct or 0.0, 8))) if pct is not None else None, anomaly_score=Decimal(str(round(abs(score), 8))), severity=severity_from_score(abs(score), rule.severity_mapping_json), status='open', detected_at=datetime.now(UTC), evidence_json={'method': rule.detection_method, 'zScore': score, 'percentageChange': pct, 'history': history[:12], 'note': 'Statistical anomaly indicator; not automatically an error.'})
    db.add(event)
    db.flush()
    write_audit_log(db, action='anomaly.detected', actor_user_id=user.id, organization_id=organization_id, entity_type='anomaly_event', entity_id=str(event.id))
    from ecotrace.modules.alerts.application import alert_service
    alert_service.create_alert(db, organization_id, alert_type='anomaly', source_type='anomaly_event', source_id=event.id, title=f'Anomaly: {rule.name}', message=f'Detected {rule.metric_type} deviation (score={abs(score):.2f}).', severity=event.severity, evidence=event.evidence_json)
    return {'created': 1, 'anomalyId': str(event.id)}

def _default_activity_scan(db: Session, user: User, organization_id: uuid.UUID) -> int:
    rule = AnomalyDetectionRule(organization_id=organization_id, code='default-activity-z', name='Default activity z-score', description='Auto-created scan rule', metric_type='activity_quantity', detection_method='z_score', threshold_config_json={'z': 2.5, 'pct': 40}, minimum_data_points=3, lookback_period=12, is_active=True)
    db.add(rule)
    db.flush()
    return int(_detect_for_rule(db, user, organization_id, rule).get('created') or 0)

def _get_event(db: Session, organization_id: uuid.UUID, anomaly_id: uuid.UUID) -> AnomalyEvent:
    row = db.execute(select(AnomalyEvent).where(AnomalyEvent.id == anomaly_id, AnomalyEvent.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Anomaly not found.')
    return row

def _ser_rule(row: AnomalyDetectionRule) -> dict[str, Any]:
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'description': row.description, 'metricType': row.metric_type, 'detectionMethod': row.detection_method, 'thresholdConfig': row.threshold_config_json, 'isActive': row.is_active, 'minimumDataPoints': row.minimum_data_points, 'lookbackPeriod': row.lookback_period}

def _ser_event(row: AnomalyEvent) -> dict[str, Any]:
    return {'id': str(row.id), 'ruleId': str(row.rule_id) if row.rule_id else None, 'entityType': row.entity_type, 'entityId': str(row.entity_id) if row.entity_id else None, 'metricCode': row.metric_code, 'observedValue': float(row.observed_value) if row.observed_value is not None else None, 'expectedValue': float(row.expected_value) if row.expected_value is not None else None, 'deviationValue': float(row.deviation_value) if row.deviation_value is not None else None, 'deviationPercentage': float(row.deviation_percentage) if row.deviation_percentage is not None else None, 'anomalyScore': float(row.anomaly_score) if row.anomaly_score is not None else None, 'severity': row.severity, 'status': row.status, 'detectedAt': row.detected_at.isoformat() if row.detected_at else None, 'evidence': row.evidence_json, 'assignedToUserId': str(row.assigned_to_user_id) if row.assigned_to_user_id else None, 'resolutionNotes': row.resolution_notes}
