from __future__ import annotations
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Query, Response
from pydantic import Field
from ecotrace.api.dependencies.auth import CurrentUser, DbSession
from ecotrace.modules.agents.application import agent_service, mcp_tools
from ecotrace.modules.alerts.application import alert_service
from ecotrace.modules.anomaly_detection.application import anomaly_service
from ecotrace.modules.automation.application import automation_service
from ecotrace.modules.data_quality.application import quality_service
from ecotrace.modules.forecasting.application import forecast_service
from ecotrace.modules.job_execution.application import job_service
from ecotrace.modules.notifications.application import notification_service
from ecotrace.modules.regulatory_intelligence.application import regulatory_service
from ecotrace.modules.scheduled_reports.application import report_service
from ecotrace.modules.supplier_monitoring.application import supplier_monitoring_service
from ecotrace.shared.domain.schemas import CamelModel
agents_router = APIRouter(prefix='/agents', tags=['Agents'])
org_router = APIRouter(prefix='/organizations/{organization_id}', tags=['Intelligence'])
notif_router = APIRouter(prefix='/notifications', tags=['Notifications'])
reg_router = APIRouter(prefix='/regulatory-documents', tags=['Regulatory'])

class ExecuteAgentRequest(CamelModel):
    prompt: str = Field(min_length=1)
    trigger_type: str = 'manual'

class ReviewComment(CamelModel):
    comment: str | None = None

class AssignRequest(CamelModel):
    user_id: UUID

class ResolveRequest(CamelModel):
    notes: str | None = None
    reason: str | None = None

class AutomationCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    trigger_type: str = 'schedule'
    trigger_config: dict[str, Any] | None = None
    condition_config: dict[str, Any] | None = None
    action_type: str = 'create_alert'
    action_config: dict[str, Any] | None = None
    approval_required: bool = False
    template_code: str | None = None

class AnomalyRuleCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    metric_type: str = 'activity_quantity'
    detection_method: str = 'z_score'
    threshold_config: dict[str, Any] | None = None
    minimum_data_points: int = 5
    lookback_period: int = 12

class ForecastCreate(CamelModel):
    code: str
    name: str
    metric_type: str = 'total_emissions'
    method: str = 'linear_trend'
    forecast_horizon: int = 6
    historical_period_count: int = 12

class ScheduledReportCreate(CamelModel):
    code: str
    name: str
    report_type: str = 'executive_sustainability_summary'
    schedule_expression: str = 'monthly'
    output_format: str = 'json'
    approval_required: bool = False
    recipient_user_ids: list[str] | None = None

class RegulatoryCreate(CamelModel):
    jurisdiction_code: str
    authority_name: str
    regulation_code: str
    title: str
    description: str | None = None
    category: str = 'climate'
    source_url: str | None = None
    effective_from: str | None = None
    is_demo: bool = True

class ApplicabilityReview(CamelModel):
    applicability_status: str
    notes: str | None = None

@agents_router.get('')
def list_agents(db: DbSession, user: CurrentUser) -> Any:
    _ = user
    return agent_service.list_agents(db)

@agents_router.get('/mcp/catalog')
def mcp_catalog(user: CurrentUser) -> Any:
    _ = user
    return mcp_tools.mcp_adapter_notes()

@agents_router.get('/{agent_code}')
def get_agent(agent_code: str, db: DbSession, user: CurrentUser) -> Any:
    _ = user
    return agent_service.get_agent(db, agent_code)

@org_router.post('/agents/{agent_code}/execute')
def execute_agent(organization_id: UUID, agent_code: str, payload: ExecuteAgentRequest, db: DbSession, user: CurrentUser) -> Any:
    result = agent_service.execute_agent(db, user, organization_id, agent_code, prompt=payload.prompt, trigger_type=payload.trigger_type)
    db.commit()
    return result

@org_router.get('/agent-executions')
def list_executions(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return agent_service.list_executions(db, user, organization_id)

@org_router.get('/agent-executions/{execution_id}')
def get_execution(organization_id: UUID, execution_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return agent_service.get_execution(db, user, organization_id, execution_id)

@org_router.post('/agent-executions/{execution_id}/cancel')
def cancel_execution(organization_id: UUID, execution_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = agent_service.cancel_execution(db, user, organization_id, execution_id)
    db.commit()
    return result

@org_router.get('/agent-action-requests')
def list_actions(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return agent_service.list_action_requests(db, user, organization_id)

@org_router.get('/agent-action-requests/{request_id}')
def get_action(organization_id: UUID, request_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return agent_service.get_action_request(db, user, organization_id, request_id)

@org_router.post('/agent-action-requests/{request_id}/approve')
def approve_action(organization_id: UUID, request_id: UUID, payload: ReviewComment, db: DbSession, user: CurrentUser) -> Any:
    result = agent_service.approve_action(db, user, organization_id, request_id, comment=payload.comment)
    db.commit()
    return result

@org_router.post('/agent-action-requests/{request_id}/reject')
def reject_action(organization_id: UUID, request_id: UUID, payload: ReviewComment, db: DbSession, user: CurrentUser) -> Any:
    result = agent_service.reject_action(db, user, organization_id, request_id, comment=payload.comment)
    db.commit()
    return result

@org_router.post('/agent-action-requests/{request_id}/execute')
def execute_action(organization_id: UUID, request_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = agent_service.execute_action(db, user, organization_id, request_id)
    db.commit()
    return result

@org_router.get('/automation-rules/templates')
def automation_templates(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    _ = (organization_id, db, user)
    return automation_service.list_templates()

@org_router.get('/automation-rules')
def list_rules(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return automation_service.list_rules(db, user, organization_id)

@org_router.post('/automation-rules')
def create_rule(organization_id: UUID, payload: AutomationCreate, db: DbSession, user: CurrentUser) -> Any:
    result = automation_service.create_rule(db, user, organization_id, code=payload.code, name=payload.name, description=payload.description, trigger_type=payload.trigger_type, trigger_config=payload.trigger_config, condition_config=payload.condition_config, action_type=payload.action_type, action_config=payload.action_config, approval_required=payload.approval_required, template_code=payload.template_code)
    db.commit()
    return result

@org_router.get('/automation-rules/{rule_id}')
def get_rule(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return automation_service.get_rule(db, user, organization_id, rule_id)

@org_router.patch('/automation-rules/{rule_id}')
def patch_rule(organization_id: UUID, rule_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = automation_service.update_rule(db, user, organization_id, rule_id, payload)
    db.commit()
    return result

@org_router.post('/automation-rules/{rule_id}/activate')
def activate_rule(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = automation_service.activate_rule(db, user, organization_id, rule_id)
    db.commit()
    return result

@org_router.post('/automation-rules/{rule_id}/pause')
def pause_rule(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = automation_service.pause_rule(db, user, organization_id, rule_id)
    db.commit()
    return result

@org_router.post('/automation-rules/{rule_id}/run')
def run_rule(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = automation_service.run_rule(db, user, organization_id, rule_id)
    db.commit()
    return result

@org_router.post('/automation-rules/{rule_id}/archive')
def archive_rule(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = automation_service.archive_rule(db, user, organization_id, rule_id)
    db.commit()
    return result

@org_router.get('/automation-rules/{rule_id}/executions')
def rule_execs(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return automation_service.list_rule_executions(db, user, organization_id, rule_id)

@org_router.get('/job-executions')
def jobs(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return job_service.list_jobs(db, user, organization_id)

@org_router.get('/job-executions/{execution_id}')
def get_job(organization_id: UUID, execution_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return job_service.get_job(db, user, organization_id, execution_id)

@org_router.post('/job-executions/{execution_id}/retry')
def retry_job(organization_id: UUID, execution_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = job_service.retry_job(db, user, organization_id, execution_id)
    db.commit()
    return result

@org_router.post('/job-executions/{execution_id}/cancel')
def cancel_job(organization_id: UUID, execution_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = job_service.cancel_job(db, user, organization_id, execution_id)
    db.commit()
    return result

@org_router.get('/anomaly-rules')
def anomaly_rules(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return anomaly_service.list_rules(db, user, organization_id)

@org_router.post('/anomaly-rules')
def create_anomaly_rule(organization_id: UUID, payload: AnomalyRuleCreate, db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.create_rule(db, user, organization_id, payload.model_dump(by_alias=True))
    db.commit()
    return result

@org_router.patch('/anomaly-rules/{rule_id}')
def patch_anomaly_rule(organization_id: UUID, rule_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.update_rule(db, user, organization_id, rule_id, payload)
    db.commit()
    return result

@org_router.post('/anomaly-rules/{rule_id}/run')
def run_anomaly_rule(organization_id: UUID, rule_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.run_rule(db, user, organization_id, rule_id)
    db.commit()
    return result

@org_router.get('/anomalies')
def anomalies(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return anomaly_service.list_anomalies(db, user, organization_id)

@org_router.get('/anomalies/{anomaly_id}')
def get_anomaly(organization_id: UUID, anomaly_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return anomaly_service.get_anomaly(db, user, organization_id, anomaly_id)

@org_router.post('/anomalies/{anomaly_id}/acknowledge')
def ack_anomaly(organization_id: UUID, anomaly_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.acknowledge(db, user, organization_id, anomaly_id)
    db.commit()
    return result

@org_router.post('/anomalies/{anomaly_id}/assign')
def assign_anomaly(organization_id: UUID, anomaly_id: UUID, payload: AssignRequest, db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.assign(db, user, organization_id, anomaly_id, payload.user_id)
    db.commit()
    return result

@org_router.post('/anomalies/{anomaly_id}/resolve')
def resolve_anomaly(organization_id: UUID, anomaly_id: UUID, payload: ResolveRequest, db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.resolve(db, user, organization_id, anomaly_id, payload.notes)
    db.commit()
    return result

@org_router.post('/anomalies/{anomaly_id}/dismiss')
def dismiss_anomaly(organization_id: UUID, anomaly_id: UUID, payload: ResolveRequest, db: DbSession, user: CurrentUser) -> Any:
    result = anomaly_service.dismiss(db, user, organization_id, anomaly_id, payload.reason or payload.notes or '')
    db.commit()
    return result

@org_router.get('/forecast-definitions')
def forecast_defs(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return forecast_service.list_definitions(db, user, organization_id)

@org_router.post('/forecast-definitions')
def create_forecast(organization_id: UUID, payload: ForecastCreate, db: DbSession, user: CurrentUser) -> Any:
    result = forecast_service.create_definition(db, user, organization_id, payload.model_dump(by_alias=True))
    db.commit()
    return result

@org_router.get('/forecast-definitions/{definition_id}')
def get_forecast_def(organization_id: UUID, definition_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return forecast_service.get_definition(db, user, organization_id, definition_id)

@org_router.patch('/forecast-definitions/{definition_id}')
def patch_forecast_def(organization_id: UUID, definition_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = forecast_service.update_definition(db, user, organization_id, definition_id, payload)
    db.commit()
    return result

@org_router.post('/forecast-definitions/{definition_id}/run')
def run_forecast(organization_id: UUID, definition_id: UUID, db: DbSession, user: CurrentUser, backtest: bool=Query(True)) -> Any:
    result = forecast_service.run_forecast(db, user, organization_id, definition_id, backtest=backtest)
    db.commit()
    return result

@org_router.get('/forecast-definitions/{definition_id}/runs')
def forecast_runs(organization_id: UUID, definition_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return forecast_service.list_runs(db, user, organization_id, definition_id)

@org_router.get('/forecast-runs/{run_id}')
def get_forecast_run(organization_id: UUID, run_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return forecast_service.get_run(db, user, organization_id, run_id)

@org_router.get('/forecast-runs/{run_id}/points')
def forecast_points(organization_id: UUID, run_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return forecast_service.get_points(db, user, organization_id, run_id)

@org_router.get('/forecasts/target-trajectory')
def trajectory(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return forecast_service.target_trajectory(db, user, organization_id)

@org_router.get('/data-quality/issues')
def dq_issues(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return quality_service.list_issues(db, user, organization_id)

@org_router.get('/data-quality/issues/{issue_id}')
def dq_issue(organization_id: UUID, issue_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return quality_service.get_issue(db, user, organization_id, issue_id)

@org_router.post('/data-quality/scan')
def dq_scan(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = quality_service.scan(db, user, organization_id)
    db.commit()
    return result

@org_router.post('/data-quality/issues/{issue_id}/assign')
def dq_assign(organization_id: UUID, issue_id: UUID, payload: AssignRequest, db: DbSession, user: CurrentUser) -> Any:
    result = quality_service.assign(db, user, organization_id, issue_id, payload.user_id)
    db.commit()
    return result

@org_router.post('/data-quality/issues/{issue_id}/resolve')
def dq_resolve(organization_id: UUID, issue_id: UUID, payload: ResolveRequest, db: DbSession, user: CurrentUser) -> Any:
    result = quality_service.resolve(db, user, organization_id, issue_id, payload.notes)
    db.commit()
    return result

@org_router.post('/data-quality/issues/{issue_id}/dismiss')
def dq_dismiss(organization_id: UUID, issue_id: UUID, payload: ResolveRequest, db: DbSession, user: CurrentUser) -> Any:
    result = quality_service.dismiss(db, user, organization_id, issue_id, payload.reason or payload.notes or '')
    db.commit()
    return result

@org_router.get('/alerts')
def alerts(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return alert_service.list_alerts(db, user, organization_id)

@org_router.get('/alerts/{alert_id}')
def get_alert(organization_id: UUID, alert_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return alert_service.get_alert(db, user, organization_id, alert_id)

@org_router.post('/alerts/{alert_id}/acknowledge')
def ack_alert(organization_id: UUID, alert_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = alert_service.acknowledge(db, user, organization_id, alert_id)
    db.commit()
    return result

@org_router.post('/alerts/{alert_id}/assign')
def assign_alert(organization_id: UUID, alert_id: UUID, payload: AssignRequest, db: DbSession, user: CurrentUser) -> Any:
    result = alert_service.assign(db, user, organization_id, alert_id, payload.user_id)
    db.commit()
    return result

@org_router.post('/alerts/{alert_id}/resolve')
def resolve_alert(organization_id: UUID, alert_id: UUID, payload: ResolveRequest, db: DbSession, user: CurrentUser) -> Any:
    result = alert_service.resolve(db, user, organization_id, alert_id, payload.notes)
    db.commit()
    return result

@notif_router.get('')
def notifications(db: DbSession, user: CurrentUser) -> Any:
    return notification_service.list_notifications(db, user)

@notif_router.get('/unread-count')
def unread(db: DbSession, user: CurrentUser) -> Any:
    return notification_service.unread_count(db, user)

@notif_router.post('/{notification_id}/read')
def read_one(notification_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = notification_service.mark_read(db, user, notification_id)
    db.commit()
    return result

@notif_router.post('/read-all')
def read_all(db: DbSession, user: CurrentUser) -> Any:
    result = notification_service.mark_all_read(db, user)
    db.commit()
    return result

@org_router.get('/notification-preferences')
def get_prefs(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return notification_service.get_preferences(db, user, organization_id)

@org_router.patch('/notification-preferences')
def patch_prefs(organization_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = notification_service.update_preferences(db, user, organization_id, payload)
    db.commit()
    return result

@org_router.get('/scheduled-reports')
def sched_reports(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return report_service.list_scheduled(db, user, organization_id)

@org_router.post('/scheduled-reports')
def create_sched(organization_id: UUID, payload: ScheduledReportCreate, db: DbSession, user: CurrentUser) -> Any:
    result = report_service.create_scheduled(db, user, organization_id, payload.model_dump(by_alias=True))
    db.commit()
    return result

@org_router.get('/scheduled-reports/{report_id}')
def get_sched(organization_id: UUID, report_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return report_service.get_scheduled(db, user, organization_id, report_id)

@org_router.patch('/scheduled-reports/{report_id}')
def patch_sched(organization_id: UUID, report_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = report_service.update_scheduled(db, user, organization_id, report_id, payload)
    db.commit()
    return result

@org_router.post('/scheduled-reports/{report_id}/activate')
def activate_sched(organization_id: UUID, report_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = report_service.activate_scheduled(db, user, organization_id, report_id)
    db.commit()
    return result

@org_router.post('/scheduled-reports/{report_id}/pause')
def pause_sched(organization_id: UUID, report_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = report_service.pause_scheduled(db, user, organization_id, report_id)
    db.commit()
    return result

@org_router.post('/scheduled-reports/{report_id}/run')
def run_sched(organization_id: UUID, report_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = report_service.run_scheduled(db, user, organization_id, report_id)
    db.commit()
    return result

@org_router.get('/generated-reports')
def gen_reports(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return report_service.list_generated(db, user, organization_id)

@org_router.get('/generated-reports/{report_id}')
def get_gen(organization_id: UUID, report_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return report_service.get_generated(db, user, organization_id, report_id)

@org_router.get('/generated-reports/{report_id}/download')
def download_gen(organization_id: UUID, report_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    name, content, media = report_service.download(db, user, organization_id, report_id)
    db.commit()
    return Response(content=content, media_type=media, headers={'Content-Disposition': f'attachment; filename="{name}"'})

@org_router.get('/supplier-monitoring')
def supplier_mon(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return supplier_monitoring_service.list_profiles(db, user, organization_id)

@org_router.get('/supplier-monitoring/{supplier_id}')
def supplier_one(organization_id: UUID, supplier_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return supplier_monitoring_service.get_profile(db, user, organization_id, supplier_id)

@org_router.patch('/supplier-monitoring/{supplier_id}')
def supplier_patch(organization_id: UUID, supplier_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = supplier_monitoring_service.update_profile(db, user, organization_id, supplier_id, payload)
    db.commit()
    return result

@org_router.post('/supplier-monitoring/{supplier_id}/assess')
def supplier_assess(organization_id: UUID, supplier_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = supplier_monitoring_service.assess(db, user, organization_id, supplier_id)
    db.commit()
    return result

@org_router.get('/supplier-monitoring/{supplier_id}/assessments')
def supplier_assessments(organization_id: UUID, supplier_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return supplier_monitoring_service.list_assessments(db, user, organization_id, supplier_id)

@reg_router.get('')
def reg_docs(db: DbSession, user: CurrentUser) -> Any:
    return regulatory_service.list_documents(db, user)

@reg_router.post('')
def create_reg(payload: RegulatoryCreate, db: DbSession, user: CurrentUser) -> Any:
    result = regulatory_service.create_document(db, user, payload.model_dump(by_alias=True))
    db.commit()
    return result

@reg_router.get('/{document_id}')
def get_reg(document_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return regulatory_service.get_document(db, user, document_id)

@reg_router.patch('/{document_id}')
def patch_reg(document_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = regulatory_service.update_document(db, user, document_id, payload)
    db.commit()
    return result

@org_router.get('/regulatory-assessments')
def reg_assessments(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return regulatory_service.list_assessments(db, user, organization_id)

@org_router.get('/regulatory-assessments/{assessment_id}')
def get_reg_assessment(organization_id: UUID, assessment_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    return regulatory_service.get_assessment(db, user, organization_id, assessment_id)

@org_router.patch('/regulatory-assessments/{assessment_id}')
def patch_reg_assessment(organization_id: UUID, assessment_id: UUID, payload: dict[str, Any], db: DbSession, user: CurrentUser) -> Any:
    result = regulatory_service.update_assessment(db, user, organization_id, assessment_id, payload)
    db.commit()
    return result

@org_router.post('/regulatory-assessments/{assessment_id}/review')
def review_reg(organization_id: UUID, assessment_id: UUID, payload: ApplicabilityReview, db: DbSession, user: CurrentUser) -> Any:
    result = regulatory_service.review_assessment(db, user, organization_id, assessment_id, applicability_status=payload.applicability_status, notes=payload.notes)
    db.commit()
    return result

@org_router.post('/regulatory-assessments/scan')
def scan_reg(organization_id: UUID, db: DbSession, user: CurrentUser) -> Any:
    result = regulatory_service.scan_org(db, user, organization_id)
    db.commit()
    return result
