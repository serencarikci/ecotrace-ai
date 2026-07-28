from __future__ import annotations
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import AutomationRule, AutomationRuleExecution, JobExecution
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_automation_manage, require_automation_read, require_automation_write
TEMPLATES: dict[str, dict[str, Any]] = {'monthly_carbon_report': {'triggerType': 'schedule', 'triggerConfig': {'expression': 'monthly', 'day': 1}, 'actionType': 'generate_report', 'actionConfig': {'reportType': 'carbon_inventory_summary'}}, 'weekly_anomaly_scan': {'triggerType': 'schedule', 'triggerConfig': {'expression': 'weekly', 'weekday': 1}, 'actionType': 'run_anomaly_detection', 'actionConfig': {}}, 'daily_data_quality_scan': {'triggerType': 'schedule', 'triggerConfig': {'expression': 'daily'}, 'actionType': 'run_data_quality_scan', 'actionConfig': {}}, 'target_risk_alert': {'triggerType': 'schedule', 'triggerConfig': {'expression': 'weekly'}, 'actionType': 'create_alert', 'actionConfig': {'alertType': 'target_risk'}}, 'failed_import_alert': {'triggerType': 'completed_import', 'triggerConfig': {'onFailure': True}, 'actionType': 'create_alert', 'actionConfig': {'alertType': 'import_failure'}}, 'quarterly_supplier_review': {'triggerType': 'schedule', 'triggerConfig': {'expression': 'quarterly'}, 'actionType': 'start_agent_execution', 'actionConfig': {'agentCode': 'supplier_review'}}, 'regulatory_effective_date_alert': {'triggerType': 'schedule', 'triggerConfig': {'expression': 'daily'}, 'actionType': 'create_alert', 'actionConfig': {'alertType': 'document_expiration'}}}

def list_templates() -> list[dict[str, Any]]:
    return [{'code': k, **v} for k, v in TEMPLATES.items()]

def list_rules(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    rows = db.execute(select(AutomationRule).where(AutomationRule.organization_id == organization_id).order_by(AutomationRule.updated_at.desc())).scalars()
    return [_ser(r) for r in rows]

def create_rule(db: Session, user: User, organization_id: uuid.UUID, *, code: str, name: str, description: str | None, trigger_type: str, trigger_config: dict[str, Any] | None, condition_config: dict[str, Any] | None, action_type: str, action_config: dict[str, Any] | None, approval_required: bool=False, template_code: str | None=None) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    if template_code:
        tpl = TEMPLATES.get(template_code)
        if not tpl:
            raise ValidationAppError('Unknown automation template.')
        trigger_type = tpl['triggerType']
        trigger_config = tpl['triggerConfig']
        action_type = tpl['actionType']
        action_config = tpl['actionConfig']
    _validate_schedule(trigger_type, trigger_config or {})
    if action_type in {'delete_records', 'approve_inventory', 'publish_passport'}:
        raise ValidationAppError('Destructive automation actions are prohibited.')
    row = AutomationRule(organization_id=organization_id, code=code.strip(), name=name.strip(), description=description, trigger_type=trigger_type, trigger_config_json=trigger_config or {}, condition_config_json=condition_config or {}, action_type=action_type, action_config_json=action_config or {}, approval_required=approval_required, status='draft', created_by_user_id=user.id, next_run_at=_next_run(trigger_type, trigger_config or {}))
    db.add(row)
    db.flush()
    write_audit_log(db, action='automation.rule.created', actor_user_id=user.id, organization_id=organization_id, entity_type='automation_rule', entity_id=str(row.id))
    return _ser(row)

def get_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID) -> dict[str, Any]:
    require_automation_read(db, user, organization_id)
    return _ser(_get(db, organization_id, rule_id))

def update_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID, payload: dict[str, Any]) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, rule_id)
    if row.status == 'archived':
        raise ValidationAppError('Archived rules cannot be updated.')
    for key, attr in {'name': 'name', 'description': 'description', 'triggerConfig': 'trigger_config_json', 'conditionConfig': 'condition_config_json', 'actionConfig': 'action_config_json', 'approvalRequired': 'approval_required'}.items():
        if key in payload:
            setattr(row, attr, payload[key])
    write_audit_log(db, action='automation.rule.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='automation_rule', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def activate_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get(db, organization_id, rule_id)
    _validate_schedule(row.trigger_type, row.trigger_config_json or {})
    row.status = 'active'
    row.approved_by_user_id = user.id
    row.next_run_at = _next_run(row.trigger_type, row.trigger_config_json or {})
    write_audit_log(db, action='automation.rule.activated', actor_user_id=user.id, organization_id=organization_id, entity_type='automation_rule', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def pause_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get(db, organization_id, rule_id)
    row.status = 'paused'
    write_audit_log(db, action='automation.rule.paused', actor_user_id=user.id, organization_id=organization_id, entity_type='automation_rule', entity_id=str(row.id))
    db.flush()
    return _ser(row)

def archive_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID) -> dict[str, Any]:
    require_automation_manage(db, user, organization_id)
    row = _get(db, organization_id, rule_id)
    row.status = 'archived'
    db.flush()
    return _ser(row)

def run_rule(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID, *, manual: bool=True) -> dict[str, Any]:
    require_automation_write(db, user, organization_id)
    row = _get(db, organization_id, rule_id)
    if row.status not in {'active', 'draft'} and (not manual):
        raise ValidationAppError('Rule is not runnable.')
    day_key = datetime.now(UTC).strftime('%Y%m%d%H')
    execution_key = hashlib.sha256(f'{row.id}:{day_key}:{row.action_type}'.encode()).hexdigest()[:40]
    existing = db.execute(select(AutomationRuleExecution).where(AutomationRuleExecution.organization_id == organization_id, AutomationRuleExecution.execution_key == execution_key)).scalar_one_or_none()
    if existing:
        raise ConflictError('Duplicate automation execution prevented.')
    settings = get_settings()
    job = JobExecution(organization_id=organization_id, job_type=f'automation:{row.action_type}', job_reference_id=row.id, execution_key=f'job-{execution_key}', status='running', scheduled_for=datetime.now(UTC), started_at=datetime.now(UTC), attempt_number=1, max_attempts=settings.job_max_attempts, worker_id='api-manual' if manual else 'scheduler', trace_id=uuid.uuid4().hex)
    db.add(job)
    exec_row = AutomationRuleExecution(organization_id=organization_id, automation_rule_id=row.id, execution_key=execution_key, status='running', started_at=datetime.now(UTC))
    db.add(exec_row)
    db.flush()
    result = _dispatch_action(db, user, organization_id, row)
    exec_row.status = 'completed'
    exec_row.completed_at = datetime.now(UTC)
    exec_row.result_summary_json = result
    job.status = 'completed'
    job.completed_at = datetime.now(UTC)
    job.result_summary_json = result
    row.last_run_at = datetime.now(UTC)
    row.last_execution_key = execution_key
    row.next_run_at = _next_run(row.trigger_type, row.trigger_config_json or {})
    write_audit_log(db, action='automation.rule.executed', actor_user_id=user.id, organization_id=organization_id, entity_type='automation_rule', entity_id=str(row.id), metadata={'executionKey': execution_key})
    db.flush()
    return {'rule': _ser(row), 'execution': _ser_exec(exec_row), 'job': _ser_job(job)}

def list_rule_executions(db: Session, user: User, organization_id: uuid.UUID, rule_id: uuid.UUID) -> list[dict[str, Any]]:
    require_automation_read(db, user, organization_id)
    _get(db, organization_id, rule_id)
    rows = db.execute(select(AutomationRuleExecution).where(AutomationRuleExecution.organization_id == organization_id, AutomationRuleExecution.automation_rule_id == rule_id).order_by(AutomationRuleExecution.created_at.desc())).scalars()
    return [_ser_exec(r) for r in rows]

def _dispatch_action(db: Session, user: User, organization_id: uuid.UUID, row: AutomationRule) -> dict[str, Any]:
    action = row.action_type
    cfg = row.action_config_json or {}
    if action == 'create_alert':
        from ecotrace.modules.alerts.application import alert_service
        alert = alert_service.create_alert(db, organization_id, alert_type=str(cfg.get('alertType') or 'automation'), source_type='automation_rule', source_id=row.id, title=f'Automation: {row.name}', message=row.description or row.name, severity='medium')
        return {'alertId': alert['id']}
    if action == 'run_anomaly_detection':
        from ecotrace.modules.anomaly_detection.application import anomaly_service
        return anomaly_service.run_org_scan(db, user, organization_id)
    if action == 'run_data_quality_scan':
        from ecotrace.modules.data_quality.application import quality_service
        return quality_service.scan(db, user, organization_id)
    if action == 'generate_report':
        from ecotrace.modules.scheduled_reports.application import report_service
        return report_service.generate_now(db, user, organization_id, report_type=str(cfg.get('reportType') or 'executive_sustainability_summary'), scheduled_report_id=None)
    if action == 'run_forecast':
        return {'status': 'queued_forecast_hook', 'config': cfg}
    if action == 'start_agent_execution':
        from ecotrace.modules.agents.application import agent_service
        return agent_service.execute_agent(db, user, organization_id, str(cfg.get('agentCode') or 'carbon_analysis'), prompt=f'Automation rule {row.code} triggered review.', trigger_type='automation_rule')
    if action == 'notify_users':
        from ecotrace.modules.notifications.application import notification_service
        return notification_service.notify_org_admins(db, organization_id, title=f'Automation {row.name}', message=row.description or 'Automation completed', notification_type='automation')
    if action == 'create_recommendation':
        return {'draftRecommendation': True, 'rule': row.code}
    if action == 'create_review_task':
        return {'draftReviewTask': True, 'rule': row.code}
    if action == 'request_human_approval':
        return {'approvalRequested': True}
    return {'status': 'noop', 'action': action}

def _validate_schedule(trigger_type: str, config: dict[str, Any]) -> None:
    if trigger_type != 'schedule':
        return
    expr = str(config.get('expression') or '')
    allowed = {'daily', 'weekly', 'monthly', 'quarterly', 'annual', 'one_time'}
    if expr in allowed:
        return
    parts = expr.split()
    if len(parts) == 5 and all((p.replace('*/', '').replace('*', '').isdigit() or p in {'*', '*/1'} or '/' in p or (',' in p) or ('-' in p) for p in parts)):
        return
    if not expr:
        raise ValidationAppError('Schedule expression required.')
    raise ValidationAppError(f'Unsupported schedule expression: {expr}')

def schedule_preview(expression: str) -> str:
    mapping = {'daily': 'Every day at 00:00 UTC', 'weekly': 'Every week (Monday) at 00:00 UTC', 'monthly': 'Monthly on day 1 at 00:00 UTC', 'quarterly': 'Every quarter on day 1 at 00:00 UTC', 'annual': 'Every year on Jan 1 at 00:00 UTC', 'one_time': 'One-time execution'}
    if expression in mapping:
        return mapping[expression]
    return f'Cron expression: {expression}'

def _next_run(trigger_type: str, config: dict[str, Any]) -> datetime | None:
    if trigger_type != 'schedule':
        return None
    now = datetime.now(UTC)
    expr = str(config.get('expression') or 'daily')
    if expr == 'daily':
        return now + timedelta(days=1)
    if expr == 'weekly':
        return now + timedelta(days=7)
    if expr == 'monthly':
        return now + timedelta(days=30)
    if expr == 'quarterly':
        return now + timedelta(days=90)
    if expr == 'annual':
        return now + timedelta(days=365)
    if expr == 'one_time':
        return now
    return now + timedelta(days=1)

def _get(db: Session, organization_id: uuid.UUID, rule_id: uuid.UUID) -> AutomationRule:
    row = db.execute(select(AutomationRule).where(AutomationRule.id == rule_id, AutomationRule.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Automation rule not found.')
    return row

def _ser(row: AutomationRule) -> dict[str, Any]:
    expr = (row.trigger_config_json or {}).get('expression')
    return {'id': str(row.id), 'code': row.code, 'name': row.name, 'description': row.description, 'triggerType': row.trigger_type, 'triggerConfig': row.trigger_config_json, 'conditionConfig': row.condition_config_json, 'actionType': row.action_type, 'actionConfig': row.action_config_json, 'approvalRequired': row.approval_required, 'status': row.status, 'lastRunAt': row.last_run_at.isoformat() if row.last_run_at else None, 'nextRunAt': row.next_run_at.isoformat() if row.next_run_at else None, 'schedulePreview': schedule_preview(str(expr)) if expr else None}

def _ser_exec(row: AutomationRuleExecution) -> dict[str, Any]:
    return {'id': str(row.id), 'executionKey': row.execution_key, 'status': row.status, 'resultSummary': row.result_summary_json, 'startedAt': row.started_at.isoformat() if row.started_at else None, 'completedAt': row.completed_at.isoformat() if row.completed_at else None}

def _ser_job(row: JobExecution) -> dict[str, Any]:
    return {'id': str(row.id), 'jobType': row.job_type, 'executionKey': row.execution_key, 'status': row.status, 'attemptNumber': row.attempt_number, 'traceId': row.trace_id}
