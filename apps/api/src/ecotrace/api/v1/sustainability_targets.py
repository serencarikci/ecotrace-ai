from __future__ import annotations
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.sustainability_targets.application import target_service
from ecotrace.modules.sustainability_targets.application.target_service import BaselineCreate, BaselineResponse, BaselineUpdate, InitiativeCreate, InitiativeResponse, InitiativeTransition, InitiativeUpdate, IntensityDefCreate, IntensityDefResponse, IntensityDefUpdate, KpiDefCreate, KpiDefResponse, KpiDefUpdate, TargetCreate, TargetResponse, TargetUpdate
from ecotrace.shared.domain.schemas import Page
intensity_router = APIRouter(prefix='/organizations/{organization_id}/intensity-metrics', tags=['Intensity Metrics'])
kpi_router = APIRouter(prefix='/organizations/{organization_id}/environmental-kpis', tags=['Environmental KPIs'])
baseline_router = APIRouter(prefix='/organizations/{organization_id}/sustainability-baselines', tags=['Sustainability Baselines'])
target_router = APIRouter(prefix='/organizations/{organization_id}/sustainability-targets', tags=['Sustainability Targets'])
initiative_router = APIRouter(prefix='/organizations/{organization_id}/reduction-initiatives', tags=['Reduction Initiatives'])

@intensity_router.get('', response_model=Page[IntensityDefResponse])
def list_intensity(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize')) -> Page[IntensityDefResponse]:
    return target_service.list_intensity_defs(db, user, organization_id, page=page, page_size=page_size)

@intensity_router.post('', response_model=IntensityDefResponse, status_code=201)
def create_intensity(organization_id: UUID, payload: IntensityDefCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> IntensityDefResponse:
    return target_service.create_intensity_def(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@intensity_router.patch('/{definition_id}', response_model=IntensityDefResponse)
def update_intensity(organization_id: UUID, definition_id: UUID, payload: IntensityDefUpdate, db: DbSession, user: CurrentUser) -> IntensityDefResponse:
    return target_service.update_intensity_def(db, user, organization_id, definition_id, payload)

@kpi_router.get('', response_model=Page[KpiDefResponse])
def list_kpis(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize')) -> Page[KpiDefResponse]:
    return target_service.list_kpi_defs(db, user, organization_id, page=page, page_size=page_size)

@kpi_router.post('', response_model=KpiDefResponse, status_code=201)
def create_kpi(organization_id: UUID, payload: KpiDefCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> KpiDefResponse:
    return target_service.create_kpi_def(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@kpi_router.patch('/{definition_id}', response_model=KpiDefResponse)
def update_kpi(organization_id: UUID, definition_id: UUID, payload: KpiDefUpdate, db: DbSession, user: CurrentUser) -> KpiDefResponse:
    return target_service.update_kpi_def(db, user, organization_id, definition_id, payload)

@baseline_router.get('', response_model=Page[BaselineResponse])
def list_baselines(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), status: str | None=None) -> Page[BaselineResponse]:
    return target_service.list_baselines(db, user, organization_id, page=page, page_size=page_size, status=status)

@baseline_router.post('', response_model=BaselineResponse, status_code=201)
def create_baseline(organization_id: UUID, payload: BaselineCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BaselineResponse:
    return target_service.create_baseline(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@baseline_router.get('/{baseline_id}', response_model=BaselineResponse)
def get_baseline(organization_id: UUID, baseline_id: UUID, db: DbSession, user: CurrentUser) -> BaselineResponse:
    return target_service.get_baseline(db, user, organization_id, baseline_id)

@baseline_router.patch('/{baseline_id}', response_model=BaselineResponse)
def update_baseline(organization_id: UUID, baseline_id: UUID, payload: BaselineUpdate, db: DbSession, user: CurrentUser) -> BaselineResponse:
    return target_service.update_baseline(db, user, organization_id, baseline_id, payload)

@baseline_router.post('/{baseline_id}/approve', response_model=BaselineResponse)
def approve_baseline(organization_id: UUID, baseline_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BaselineResponse:
    return target_service.approve_baseline(db, user, organization_id, baseline_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@baseline_router.post('/{baseline_id}/archive', response_model=BaselineResponse)
def archive_baseline(organization_id: UUID, baseline_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BaselineResponse:
    return target_service.archive_baseline(db, user, organization_id, baseline_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@target_router.get('', response_model=Page[TargetResponse])
def list_targets(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), status: str | None=None) -> Page[TargetResponse]:
    return target_service.list_targets(db, user, organization_id, page=page, page_size=page_size, status=status)

@target_router.post('', response_model=TargetResponse, status_code=201)
def create_target(organization_id: UUID, payload: TargetCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> TargetResponse:
    return target_service.create_target(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@target_router.get('/{target_id}', response_model=TargetResponse)
def get_target(organization_id: UUID, target_id: UUID, db: DbSession, user: CurrentUser) -> TargetResponse:
    return target_service.get_target(db, user, organization_id, target_id)

@target_router.patch('/{target_id}', response_model=TargetResponse)
def update_target(organization_id: UUID, target_id: UUID, payload: TargetUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> TargetResponse:
    return target_service.update_target(db, user, organization_id, target_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@target_router.post('/{target_id}/approve', response_model=TargetResponse)
def approve_target(organization_id: UUID, target_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> TargetResponse:
    return target_service.approve_target(db, user, organization_id, target_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@target_router.get('/{target_id}/progress')
def get_target_progress(organization_id: UUID, target_id: UUID, db: DbSession, user: CurrentUser, inventory_id: UUID | None=Query(None, alias='inventoryId'), allow_provisional: bool=Query(False, alias='allowProvisional')) -> dict[str, Any]:
    return target_service.target_progress(db, user, organization_id, target_id, inventory_id=inventory_id, allow_provisional=allow_provisional)

@initiative_router.get('', response_model=Page[InitiativeResponse])
def list_initiatives(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), status: str | None=None) -> Page[InitiativeResponse]:
    return target_service.list_initiatives(db, user, organization_id, page=page, page_size=page_size, status=status)

@initiative_router.post('', response_model=InitiativeResponse, status_code=201)
def create_initiative(organization_id: UUID, payload: InitiativeCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> InitiativeResponse:
    return target_service.create_initiative(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@initiative_router.get('/{initiative_id}', response_model=InitiativeResponse)
def get_initiative(organization_id: UUID, initiative_id: UUID, db: DbSession, user: CurrentUser) -> InitiativeResponse:
    return target_service.get_initiative(db, user, organization_id, initiative_id)

@initiative_router.patch('/{initiative_id}', response_model=InitiativeResponse)
def update_initiative(organization_id: UUID, initiative_id: UUID, payload: InitiativeUpdate, db: DbSession, user: CurrentUser) -> InitiativeResponse:
    return target_service.update_initiative(db, user, organization_id, initiative_id, payload)

@initiative_router.post('/{initiative_id}/transition', response_model=InitiativeResponse)
def transition_initiative(organization_id: UUID, initiative_id: UUID, payload: InitiativeTransition, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> InitiativeResponse:
    return target_service.transition_initiative(db, user, organization_id, initiative_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)
