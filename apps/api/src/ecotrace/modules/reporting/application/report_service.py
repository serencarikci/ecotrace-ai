from __future__ import annotations
import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any
from sqlalchemy.orm import Session
from ecotrace.modules.analytics.application import query_service
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.scenarios.application import scenario_service
from ecotrace.modules.sustainability_targets.application import target_service
DISCLAIMER = 'EcoTrace AI analytics report. Values are derived from authorized organization data. Demo emission factors are not suitable for regulatory reporting.'

def _meta(organization_id: uuid.UUID, report_type: str) -> dict[str, Any]:
    return {'organizationId': str(organization_id), 'reportType': report_type, 'generatedAt': datetime.now(UTC).isoformat(), 'disclaimer': DISCLAIMER}

def executive_report(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    dashboard = query_service.dashboard(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
    recommendations = query_service.recommendations(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
    targets = target_service.list_targets(db, user, organization_id, page=1, page_size=50, status='active')
    return {'metadata': _meta(organization_id, 'executive'), 'dashboard': dashboard, 'activeTargets': [t.model_dump(mode='json', by_alias=True) for t in targets.items], 'recommendations': recommendations}

def inventory_summary_report(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    dashboard = query_service.dashboard(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
    return {'metadata': _meta(organization_id, 'inventory_summary'), 'summary': dashboard['summary'], 'scopeDistribution': dashboard['scopeDistribution'], 'categoryDistribution': dashboard['categoryDistribution'], 'facilityTotals': dashboard['facilityTotals'], 'inventoryMetadata': dashboard['metadata']}

def target_progress_report(db: Session, user: User, organization_id: uuid.UUID, *, inventory_id: uuid.UUID | None=None, allow_provisional: bool=False) -> dict[str, Any]:
    targets = target_service.list_targets(db, user, organization_id, page=1, page_size=100)
    rows = []
    for target in targets.items:
        rows.append(target_service.target_progress(db, user, organization_id, target.id, inventory_id=inventory_id, allow_provisional=allow_provisional))
    return {'metadata': _meta(organization_id, 'target_progress'), 'items': rows}

def scenario_comparison_report(db: Session, user: User, organization_id: uuid.UUID, *, scenario_id: uuid.UUID | None=None) -> dict[str, Any]:
    scenarios = scenario_service.list_scenarios(db, user, organization_id, page=1, page_size=100)
    items = []
    for scenario in scenarios.items:
        if scenario_id and scenario.id != scenario_id:
            continue
        runs = scenario_service.list_runs(db, user, organization_id, scenario.id)
        latest = runs[0] if runs else None
        items.append({'scenario': scenario.model_dump(mode='json', by_alias=True), 'latestRun': None if latest is None else latest.model_dump(mode='json', by_alias=True)})
    return {'metadata': _meta(organization_id, 'scenario_comparison'), 'items': items}

def to_csv(report: dict[str, Any], report_type: str) -> tuple[str, str]:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['reportType', report_type])
    writer.writerow(['generatedAt', report['metadata']['generatedAt']])
    writer.writerow(['disclaimer', report['metadata']['disclaimer']])
    writer.writerow([])
    if report_type == 'executive':
        summary = report['dashboard']['summary']
        writer.writerow(['metric', 'value'])
        for key, value in summary.items():
            if isinstance(value, dict):
                writer.writerow([key, value.get('name') or value.get('totalKgCo2e')])
            else:
                writer.writerow([key, value])
    elif report_type == 'inventory_summary':
        writer.writerow(['section', 'name', 'totalKgCo2e'])
        for row in report.get('categoryDistribution', []):
            writer.writerow(['category', row.get('name'), row.get('totalKgCo2e')])
        for row in report.get('facilityTotals', []):
            writer.writerow(['facility', row.get('name'), row.get('totalKgCo2e')])
    elif report_type == 'target_progress':
        writer.writerow(['targetCode', 'targetName', 'status', 'progressPercentage', 'currentValue', 'targetValue'])
        for item in report.get('items', []):
            target = item.get('target', {})
            progress = item.get('progress', {})
            writer.writerow([target.get('code'), target.get('name'), progress.get('status'), progress.get('progressPercentage'), progress.get('currentValue'), progress.get('targetValue')])
    elif report_type == 'scenario_comparison':
        writer.writerow(['scenarioCode', 'scenarioName', 'runNumber', 'baselineTotalKgCo2e', 'scenarioTotalKgCo2e', 'reductionKgCo2e', 'reductionPercentage'])
        for item in report.get('items', []):
            scenario = item.get('scenario', {})
            run = item.get('latestRun') or {}
            writer.writerow([scenario.get('code'), scenario.get('name'), run.get('runNumber'), run.get('baselineTotalKgCo2e'), run.get('scenarioTotalKgCo2e'), run.get('reductionKgCo2e'), run.get('reductionPercentage')])
    filename = f"ecotrace-{report_type}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.csv"
    return (filename, buffer.getvalue())
