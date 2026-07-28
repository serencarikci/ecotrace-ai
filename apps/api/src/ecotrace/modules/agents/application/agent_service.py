from __future__ import annotations
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import AuthorizationError, NotFoundError, ValidationAppError
from ecotrace.core.phase7_constants import AGENT_CODES, CONTROLLED_WRITE_TOOLS, FORBIDDEN_AGENT_ACTIONS, READ_ONLY_TOOLS
from ecotrace.modules.agents.application.security import detect_prompt_injection, redact_secrets
from ecotrace.modules.ai_copilot.application.tools import run_tools
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.production_operations.infrastructure.models import AgentActionRequest, AgentDefinition, AgentExecution, AgentTool, AgentToolCall, Alert
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_agent_execute, require_ai_read, require_approval_review

def ensure_catalog(db: Session) -> None:
    if db.execute(select(func.count()).select_from(AgentDefinition)).scalar_one() > 0:
        return
    defs = [('carbon_analysis', 'Carbon Analysis Agent', 'Summarize inventories and emission breakdowns.', ['get_carbon_inventory_summary', 'compare_carbon_inventories', 'get_facility_emissions', 'create_draft_recommendation']), ('data_quality', 'Data Quality Agent', 'Inspect data quality issues and propose reviews.', ['get_data_quality_issues', 'get_activity_records', 'create_draft_corrective_action']), ('target_monitoring', 'Target Monitoring Agent', 'Explain target progress and trajectory risks.', ['get_target_progress', 'create_draft_target_review']), ('report_generation', 'Report Generation Agent', 'Draft sustainability report narratives.', ['get_scheduled_report_status', 'create_draft_report']), ('supplier_review', 'Supplier Review Agent', 'Review supplier sustainability evidence.', ['get_supplier_sustainability_data', 'create_draft_recommendation']), ('regulatory_document', 'Regulatory Document Agent', 'Summarize regulatory documents with citations.', ['search_organization_documents', 'retrieve_cited_evidence'])]
    for code, name, desc, tools in defs:
        db.add(AgentDefinition(code=code, name=name, description=desc, allowed_tools_json=tools, required_permissions_json=['ai_read'], approval_policy='write_only', is_enabled=True))
    for tool in sorted(READ_ONLY_TOOLS | CONTROLLED_WRITE_TOOLS):
        db.add(AgentTool(tool_code=tool, description=tool.replace('_', ' '), required_permission='ai_read' if tool in READ_ONLY_TOOLS else 'ai_write', write_classification='read' if tool in READ_ONLY_TOOLS else 'write', approval_required=tool in CONTROLLED_WRITE_TOOLS, is_enabled=True))
    db.flush()

def list_agents(db: Session) -> list[dict[str, Any]]:
    ensure_catalog(db)
    rows = db.execute(select(AgentDefinition).order_by(AgentDefinition.code.asc())).scalars()
    return [_ser_agent(r) for r in rows]

def get_agent(db: Session, agent_code: str) -> dict[str, Any]:
    ensure_catalog(db)
    row = db.execute(select(AgentDefinition).where(AgentDefinition.code == agent_code)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Agent not found.')
    return _ser_agent(row)

def execute_agent(db: Session, user: User, organization_id: uuid.UUID, agent_code: str, *, prompt: str, trigger_type: str='manual') -> dict[str, Any]:
    require_agent_execute(db, user, organization_id)
    ensure_catalog(db)
    if agent_code not in AGENT_CODES:
        raise ValidationAppError('Unknown agent code.')
    if detect_prompt_injection(prompt):
        raise ValidationAppError('Prompt failed injection safety checks.')
    agent = db.execute(select(AgentDefinition).where(AgentDefinition.code == agent_code, AgentDefinition.is_enabled.is_(True))).scalar_one_or_none()
    if agent is None:
        raise NotFoundError('Agent not found or disabled.')
    settings = get_settings()
    trace_id = uuid.uuid4().hex
    execution = AgentExecution(organization_id=organization_id, agent_code=agent_code, trigger_type=trigger_type, status='running', started_at=datetime.now(UTC), triggered_by_user_id=user.id, model_provider='local_grounded', model_name='ecotrace-agent', trace_id=trace_id)
    db.add(execution)
    db.flush()
    write_audit_log(db, action='agent.execution.started', actor_user_id=user.id, organization_id=organization_id, entity_type='agent_execution', entity_id=str(execution.id), metadata={'agentCode': agent_code, 'traceId': trace_id})
    allowed = set(agent.allowed_tools_json or [])
    tool_results: list[dict[str, Any]] = []
    action_requests: list[dict[str, Any]] = []
    call_count = 0
    for tool_code in list(allowed)[:settings.agent_max_tool_calls]:
        if tool_code in FORBIDDEN_AGENT_ACTIONS:
            raise AuthorizationError('Forbidden agent action.')
        if tool_code not in READ_ONLY_TOOLS and tool_code not in CONTROLLED_WRITE_TOOLS:
            continue
        call_count += 1
        if tool_code in READ_ONLY_TOOLS:
            output = _run_readonly_tool(db, user, organization_id, tool_code, prompt)
            db.add(AgentToolCall(organization_id=organization_id, agent_execution_id=execution.id, tool_code=tool_code, input_json=redact_secrets({'prompt': prompt[:500]}), output_json=redact_secrets(output), status='completed'))
            tool_results.append({'tool': tool_code, 'result': output})
        else:
            req = AgentActionRequest(organization_id=organization_id, agent_execution_id=execution.id, action_type=tool_code, title=f'Proposed {tool_code}', description=f'Agent {agent_code} proposes controlled write: {tool_code}', input_payload_json=redact_secrets({'prompt': prompt[:500]}), proposed_changes_json={'action': tool_code, 'draft': True, 'summary': prompt[:240]}, risk_level='medium' if tool_code != 'create_draft_automation_rule' else 'high', status='pending', requested_by_user_id=user.id, expires_at=datetime.now(UTC) + timedelta(days=7))
            db.add(req)
            db.flush()
            action_requests.append(_ser_action(req))
            db.add(AgentToolCall(organization_id=organization_id, agent_execution_id=execution.id, tool_code=tool_code, input_json={'queued_for_approval': True}, output_json={'actionRequestId': str(req.id)}, status='awaiting_approval'))
    summary = {'agentCode': agent_code, 'tools': tool_results, 'pendingApprovals': action_requests, 'citations': [{'label': f'T{i + 1}', 'documentName': t['tool'], 'databaseSource': 'tool'} for i, t in enumerate(tool_results)], 'disclaimer': 'Grounded agent summary using allowlisted tools only.'}
    execution.tool_call_count = call_count
    execution.result_summary_json = summary
    execution.rationale = f'Executed {call_count} allowlisted tool(s). {len(action_requests)} write proposal(s) require human approval.'
    execution.status = 'awaiting_approval' if action_requests else 'completed'
    execution.completed_at = datetime.now(UTC)
    execution.prompt_tokens = max(1, len(prompt) // 4)
    execution.completion_tokens = max(1, len(str(summary)) // 4)
    write_audit_log(db, action='agent.execution.completed', actor_user_id=user.id, organization_id=organization_id, entity_type='agent_execution', entity_id=str(execution.id), metadata={'status': execution.status})
    db.flush()
    return _ser_execution(execution)

def list_executions(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    rows = db.execute(select(AgentExecution).where(AgentExecution.organization_id == organization_id).order_by(AgentExecution.created_at.desc()).limit(100)).scalars()
    return [_ser_execution(r) for r in rows]

def get_execution(db: Session, user: User, organization_id: uuid.UUID, execution_id: uuid.UUID) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    row = db.execute(select(AgentExecution).where(AgentExecution.id == execution_id, AgentExecution.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Execution not found.')
    calls = db.execute(select(AgentToolCall).where(AgentToolCall.agent_execution_id == row.id)).scalars()
    payload = _ser_execution(row)
    payload['toolCalls'] = [{'toolCode': c.tool_code, 'status': c.status, 'output': c.output_json} for c in calls]
    return payload

def cancel_execution(db: Session, user: User, organization_id: uuid.UUID, execution_id: uuid.UUID) -> dict[str, Any]:
    require_agent_execute(db, user, organization_id)
    row = db.execute(select(AgentExecution).where(AgentExecution.id == execution_id, AgentExecution.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Execution not found.')
    if row.status in {'completed', 'failed', 'cancelled'}:
        raise ValidationAppError('Execution cannot be cancelled.')
    row.status = 'cancelled'
    row.completed_at = datetime.now(UTC)
    db.flush()
    return _ser_execution(row)

def list_action_requests(db: Session, user: User, organization_id: uuid.UUID) -> list[dict[str, Any]]:
    require_ai_read(db, user, organization_id)
    rows = db.execute(select(AgentActionRequest).where(AgentActionRequest.organization_id == organization_id).order_by(AgentActionRequest.created_at.desc()).limit(100)).scalars()
    return [_ser_action(r) for r in rows]

def get_action_request(db: Session, user: User, organization_id: uuid.UUID, request_id: uuid.UUID) -> dict[str, Any]:
    require_ai_read(db, user, organization_id)
    row = _get_action(db, organization_id, request_id)
    return _ser_action(row)

def approve_action(db: Session, user: User, organization_id: uuid.UUID, request_id: uuid.UUID, *, comment: str | None=None) -> dict[str, Any]:
    require_approval_review(db, user, organization_id)
    row = _get_action(db, organization_id, request_id)
    _ensure_pending(row)
    if row.risk_level in {'high', 'critical'}:
        require_approval_review(db, user, organization_id)
    row.status = 'approved'
    row.reviewed_by_user_id = user.id
    row.review_comment = comment
    row.approved_at = datetime.now(UTC)
    write_audit_log(db, action='agent.action.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='agent_action_request', entity_id=str(row.id))
    db.flush()
    return _ser_action(row)

def reject_action(db: Session, user: User, organization_id: uuid.UUID, request_id: uuid.UUID, *, comment: str | None=None) -> dict[str, Any]:
    require_approval_review(db, user, organization_id)
    row = _get_action(db, organization_id, request_id)
    _ensure_pending(row)
    row.status = 'rejected'
    row.reviewed_by_user_id = user.id
    row.review_comment = comment
    row.rejected_at = datetime.now(UTC)
    write_audit_log(db, action='agent.action.rejected', actor_user_id=user.id, organization_id=organization_id, entity_type='agent_action_request', entity_id=str(row.id))
    db.flush()
    return _ser_action(row)

def execute_action(db: Session, user: User, organization_id: uuid.UUID, request_id: uuid.UUID) -> dict[str, Any]:
    require_approval_review(db, user, organization_id)
    row = _get_action(db, organization_id, request_id)
    if row.status != 'approved':
        raise ValidationAppError('Only approved requests can be executed.')
    if row.expires_at and row.expires_at < datetime.now(UTC):
        row.status = 'expired'
        db.flush()
        raise ValidationAppError('Action request expired.')
    artifact: dict[str, Any] = {'type': 'draft', 'payload': row.proposed_changes_json, 'createdAt': datetime.now(UTC).isoformat()}
    result: dict[str, Any] = {'executed': True, 'actionType': row.action_type, 'artifact': artifact}
    if row.action_type == 'acknowledge_alert':
        alert_id = (row.proposed_changes_json or {}).get('alertId')
        if alert_id:
            alert = db.execute(select(Alert).where(Alert.id == uuid.UUID(str(alert_id)), Alert.organization_id == organization_id)).scalar_one_or_none()
            if alert and alert.status == 'open':
                alert.status = 'acknowledged'
                alert.acknowledged_at = datetime.now(UTC)
                artifact['alertStatus'] = 'acknowledged'
    row.status = 'executed'
    row.executed_at = datetime.now(UTC)
    row.execution_result_json = result
    write_audit_log(db, action='agent.action.executed', actor_user_id=user.id, organization_id=organization_id, entity_type='agent_action_request', entity_id=str(row.id), metadata={'actionType': row.action_type})
    db.flush()
    return _ser_action(row)

def _run_readonly_tool(db: Session, user: User, organization_id: uuid.UUID, tool_code: str, prompt: str) -> dict[str, Any]:
    mapped = {'get_carbon_inventory_summary': 'summarize_inventory', 'compare_carbon_inventories': 'compare_inventories', 'get_facility_emissions': 'highest_emitting_facility', 'get_target_progress': 'explain_target_progress', 'get_product_footprint': 'summarize_product_footprint', 'get_digital_product_passport': 'summarize_passport', 'get_scenario_results': 'compare_scenarios', 'search_organization_documents': 'find_related_documents', 'retrieve_cited_evidence': 'locate_evidence'}
    action = mapped.get(tool_code)
    if action:
        results = run_tools(db, user, organization_id, question=prompt, actions=[action])
        return results[0]['result'] if results else {'summary': 'No data'}
    if tool_code == 'get_data_quality_issues':
        from ecotrace.modules.production_operations.infrastructure.models import DataQualityIssue
        count = db.execute(select(func.count()).select_from(DataQualityIssue).where(DataQualityIssue.organization_id == organization_id, DataQualityIssue.status == 'open')).scalar_one()
        return {'summary': f'Open data quality issues: {count}', 'openCount': count}
    if tool_code == 'get_anomaly_results':
        from ecotrace.modules.production_operations.infrastructure.models import AnomalyEvent
        count = db.execute(select(func.count()).select_from(AnomalyEvent).where(AnomalyEvent.organization_id == organization_id, AnomalyEvent.status == 'open')).scalar_one()
        return {'summary': f'Open anomalies: {count}', 'openCount': count}
    if tool_code == 'get_supplier_sustainability_data':
        from ecotrace.modules.production_operations.infrastructure.models import SupplierMonitoringProfile
        count = db.execute(select(func.count()).select_from(SupplierMonitoringProfile).where(SupplierMonitoringProfile.organization_id == organization_id)).scalar_one()
        return {'summary': f'Monitored suppliers: {count}', 'count': count}
    if tool_code == 'get_scheduled_report_status':
        from ecotrace.modules.production_operations.infrastructure.models import ScheduledReport
        count = db.execute(select(func.count()).select_from(ScheduledReport).where(ScheduledReport.organization_id == organization_id, ScheduledReport.status == 'active')).scalar_one()
        return {'summary': f'Active scheduled reports: {count}', 'count': count}
    if tool_code in {'get_activity_records', 'get_lca_results'}:
        return {'summary': f'Tool {tool_code} acknowledged via application service boundary.'}
    return {'summary': 'No result'}

def _get_action(db: Session, organization_id: uuid.UUID, request_id: uuid.UUID) -> AgentActionRequest:
    row = db.execute(select(AgentActionRequest).where(AgentActionRequest.id == request_id, AgentActionRequest.organization_id == organization_id)).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Action request not found.')
    return row

def _ensure_pending(row: AgentActionRequest) -> None:
    if row.status != 'pending':
        raise ValidationAppError('Action request is not pending.')
    if row.expires_at and row.expires_at < datetime.now(UTC):
        row.status = 'expired'
        raise ValidationAppError('Action request expired.')

def _ser_agent(row: AgentDefinition) -> dict[str, Any]:
    return {'code': row.code, 'name': row.name, 'description': row.description, 'allowedTools': row.allowed_tools_json or [], 'requiredPermissions': row.required_permissions_json or [], 'maxExecutionSeconds': row.max_execution_seconds, 'maxToolCalls': row.max_tool_calls, 'maxTokenUsage': row.max_token_usage, 'approvalPolicy': row.approval_policy, 'isEnabled': row.is_enabled}

def _ser_execution(row: AgentExecution) -> dict[str, Any]:
    return {'id': str(row.id), 'organizationId': str(row.organization_id), 'agentCode': row.agent_code, 'triggerType': row.trigger_type, 'status': row.status, 'startedAt': row.started_at.isoformat() if row.started_at else None, 'completedAt': row.completed_at.isoformat() if row.completed_at else None, 'toolCallCount': row.tool_call_count, 'resultSummary': row.result_summary_json, 'rationale': row.rationale, 'traceId': row.trace_id, 'modelProvider': row.model_provider, 'promptTokens': row.prompt_tokens, 'completionTokens': row.completion_tokens, 'estimatedCost': float(row.estimated_cost) if row.estimated_cost is not None else 0.0}

def _ser_action(row: AgentActionRequest) -> dict[str, Any]:
    return {'id': str(row.id), 'organizationId': str(row.organization_id), 'agentExecutionId': str(row.agent_execution_id) if row.agent_execution_id else None, 'actionType': row.action_type, 'title': row.title, 'description': row.description, 'proposedChanges': row.proposed_changes_json, 'riskLevel': row.risk_level, 'status': row.status, 'reviewComment': row.review_comment, 'approvedAt': row.approved_at.isoformat() if row.approved_at else None, 'rejectedAt': row.rejected_at.isoformat() if row.rejected_at else None, 'executedAt': row.executed_at.isoformat() if row.executed_at else None, 'executionResult': row.execution_result_json, 'expiresAt': row.expires_at.isoformat() if row.expires_at else None}
