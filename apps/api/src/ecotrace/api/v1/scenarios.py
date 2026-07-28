from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.scenarios.application import scenario_service
from ecotrace.modules.scenarios.application.scenario_service import AssumptionCreate, AssumptionResponse, ScenarioCreate, ScenarioResponse, ScenarioRunResponse, ScenarioUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(prefix='/organizations/{organization_id}/scenarios', tags=['Scenarios'])

@router.get('', response_model=Page[ScenarioResponse])
def list_scenarios(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), status: str | None=None) -> Page[ScenarioResponse]:
    return scenario_service.list_scenarios(db, user, organization_id, page=page, page_size=page_size, status=status)

@router.post('', response_model=ScenarioResponse, status_code=201)
def create_scenario(organization_id: UUID, payload: ScenarioCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ScenarioResponse:
    return scenario_service.create_scenario(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/{scenario_id}', response_model=ScenarioResponse)
def get_scenario(organization_id: UUID, scenario_id: UUID, db: DbSession, user: CurrentUser) -> ScenarioResponse:
    return scenario_service.get_scenario(db, user, organization_id, scenario_id)

@router.patch('/{scenario_id}', response_model=ScenarioResponse)
def update_scenario(organization_id: UUID, scenario_id: UUID, payload: ScenarioUpdate, db: DbSession, user: CurrentUser) -> ScenarioResponse:
    return scenario_service.update_scenario(db, user, organization_id, scenario_id, payload)

@router.get('/{scenario_id}/assumptions', response_model=list[AssumptionResponse])
def list_assumptions(organization_id: UUID, scenario_id: UUID, db: DbSession, user: CurrentUser) -> list[AssumptionResponse]:
    return scenario_service.list_assumptions(db, user, organization_id, scenario_id)

@router.post('/{scenario_id}/assumptions', response_model=AssumptionResponse, status_code=201)
def add_assumption(organization_id: UUID, scenario_id: UUID, payload: AssumptionCreate, db: DbSession, user: CurrentUser) -> AssumptionResponse:
    return scenario_service.add_assumption(db, user, organization_id, scenario_id, payload)

@router.post('/{scenario_id}/validate')
def validate_scenario(organization_id: UUID, scenario_id: UUID, db: DbSession, user: CurrentUser) -> dict[str, object]:
    return scenario_service.validate_scenario(db, user, organization_id, scenario_id)

@router.post('/{scenario_id}/calculate', response_model=ScenarioRunResponse)
def calculate_scenario(organization_id: UUID, scenario_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ScenarioRunResponse:
    return scenario_service.calculate_scenario(db, user, organization_id, scenario_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/{scenario_id}/runs', response_model=list[ScenarioRunResponse])
def list_runs(organization_id: UUID, scenario_id: UUID, db: DbSession, user: CurrentUser) -> list[ScenarioRunResponse]:
    return scenario_service.list_runs(db, user, organization_id, scenario_id)

@router.get('/{scenario_id}/runs/{run_id}', response_model=ScenarioRunResponse)
def get_run(organization_id: UUID, scenario_id: UUID, run_id: UUID, db: DbSession, user: CurrentUser) -> ScenarioRunResponse:
    return scenario_service.get_run(db, user, organization_id, scenario_id, run_id)

@router.post('/{scenario_id}/archive', response_model=ScenarioResponse)
def archive_scenario(organization_id: UUID, scenario_id: UUID, db: DbSession, user: CurrentUser) -> ScenarioResponse:
    return scenario_service.archive_scenario(db, user, organization_id, scenario_id)
