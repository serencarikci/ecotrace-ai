from __future__ import annotations
from typing import Any, Literal
from uuid import UUID
from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from ecotrace.api.dependencies.auth import CurrentUser, DbSession
from ecotrace.modules.reporting.application import report_service
router = APIRouter(prefix='/organizations/{organization_id}/reports', tags=['Reports'])

def _maybe_csv(report: dict[str, Any], report_type: str, fmt: str) -> dict[str, Any] | PlainTextResponse:
    if fmt != 'csv':
        return report
    filename, content = report_service.to_csv(report, report_type)
    return PlainTextResponse(content, media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})

@router.get('/executive')
def executive_report(organization_id: UUID, db: DbSession, user: CurrentUser, format: Literal['json', 'csv']=Query('json'), inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> Any:
    report = report_service.executive_report(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
    return _maybe_csv(report, 'executive', format)

@router.get('/inventory-summary')
def inventory_summary_report(organization_id: UUID, db: DbSession, user: CurrentUser, format: Literal['json', 'csv']=Query('json'), inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> Any:
    report = report_service.inventory_summary_report(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
    return _maybe_csv(report, 'inventory_summary', format)

@router.get('/target-progress')
def target_progress_report(organization_id: UUID, db: DbSession, user: CurrentUser, format: Literal['json', 'csv']=Query('json'), inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> Any:
    report = report_service.target_progress_report(db, user, organization_id, inventory_id=inventory_id, allow_provisional=allow_provisional)
    return _maybe_csv(report, 'target_progress', format)

@router.get('/scenario-comparison')
def scenario_comparison_report(organization_id: UUID, db: DbSession, user: CurrentUser, format: Literal['json', 'csv']=Query('json'), scenario_id: UUID | None=Query(None, alias='scenarioId')) -> Any:
    report = report_service.scenario_comparison_report(db, user, organization_id, scenario_id=scenario_id)
    return _maybe_csv(report, 'scenario_comparison', format)
