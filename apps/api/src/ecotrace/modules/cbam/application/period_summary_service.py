from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.export_context import ExportDataContext, load_export_context
from ecotrace.modules.cbam.application.export_readiness_service import assess_export_readiness
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel


class PeriodSummaryResponse(CamelModel):
    title: str
    organization_id: uuid.UUID
    organization_name: str
    reporting_period_binding_id: uuid.UUID
    reporting_period_code: str
    readiness_status: str
    metrics: dict[str, Any]
    warnings: list[str]
    official_mapping_blocked: bool
    calculation_run_id: uuid.UUID | None
    installations: list[dict[str, Any]]
    disclaimer: str


def render_summary_json(ctx: ExportDataContext, readiness_status: str) -> dict[str, Any]:
    return {
        'title': 'SKDM Period Summary',
        'organizationId': str(ctx.organization.id),
        'organizationName': ctx.organization.name,
        'reportingPeriodBindingId': str(ctx.binding.id),
        'reportingPeriodCode': ctx.period.code,
        'readinessStatus': readiness_status,
        'metrics': {
            k: (str(v) if hasattr(v, 'as_tuple') else v) for k, v in ctx.summary_metrics.items()
        },
        'warnings': ctx.warnings,
        'officialMappingBlocked': True,
        'calculationRunId': str(ctx.calculation_run.id) if ctx.calculation_run else None,
        'installations': [
            {'id': str(i.id), 'code': i.code, 'name': i.name} for i in ctx.installations
        ],
        'traceability': ctx.mapped_trace_ids,
        'disclaimer': (
            'SKDM Period Summary is an internal EcoTrace summary. '
            'It is not an official regulatory CBAM submission.'
        ),
    }


def render_summary_html(summary: dict[str, Any]) -> str:
    metrics = summary.get('metrics') or {}
    warnings = summary.get('warnings') or []
    rows = ''.join(
        f'<tr><td>{key}</td><td>{value}</td></tr>' for key, value in metrics.items()
    )
    warn_items = ''.join(f'<li>{w}</li>' for w in warnings) or '<li>None</li>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>SKDM Period Summary</title></head>
<body>
  <h1>SKDM Period Summary</h1>
  <p><strong>Organization:</strong> {summary.get('organizationName')}</p>
  <p><strong>Period:</strong> {summary.get('reportingPeriodCode')}</p>
  <p><strong>Readiness:</strong> {summary.get('readinessStatus')}</p>
  <p><em>{summary.get('disclaimer')}</em></p>
  <h2>Metrics</h2>
  <table border="1" cellpadding="4" cellspacing="0">
    <tr><th>Metric</th><th>Value</th></tr>
    {rows}
  </table>
  <h2>Warnings</h2>
  <ul>{warn_items}</ul>
</body>
</html>
"""


def get_period_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> PeriodSummaryResponse:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    readiness = assess_export_readiness(db, user, organization_id, binding_id)
    ctx = load_export_context(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        calculation_run_id=readiness.calculation_run_id,
    )
    ctx.summary_metrics['export_readiness'] = readiness.status
    payload = render_summary_json(ctx, readiness.status)
    return PeriodSummaryResponse(
        title=str(payload['title']),
        organization_id=organization_id,
        organization_name=ctx.organization.name,
        reporting_period_binding_id=binding_id,
        reporting_period_code=ctx.period.code,
        readiness_status=readiness.status,
        metrics=payload['metrics'],
        warnings=list(payload['warnings']),
        official_mapping_blocked=True,
        calculation_run_id=readiness.calculation_run_id,
        installations=list(payload['installations']),
        disclaimer=str(payload['disclaimer']),
    )
