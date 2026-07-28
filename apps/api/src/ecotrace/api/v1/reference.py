from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.reference_data.application import reference_service
from ecotrace.modules.reference_data.application.reference_service import ActivityTypeCreate, ActivityTypeResponse, ActivityTypeUpdate, UnitCreate, UnitResponse, UnitUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(prefix='/reference', tags=['Reference Data'])

@router.get('/units', response_model=Page[UnitResponse])
def list_units(db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(50, ge=1, le=200, alias='pageSize'), active_only: bool=Query(True, alias='activeOnly'), dimension: str | None=None, search: str | None=None) -> Page[UnitResponse]:
    return reference_service.list_units(db, user, page=page, page_size=page_size, active_only=active_only, dimension=dimension, search=search)

@router.post('/units', response_model=UnitResponse, status_code=201)
def create_unit(payload: UnitCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> UnitResponse:
    return reference_service.create_unit(db, user, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.patch('/units/{unit_id}', response_model=UnitResponse)
def update_unit(unit_id: UUID, payload: UnitUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> UnitResponse:
    return reference_service.update_unit(db, user, unit_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/activity-types', response_model=Page[ActivityTypeResponse])
def list_activity_types(db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(50, ge=1, le=200, alias='pageSize'), active_only: bool=Query(True, alias='activeOnly'), category: str | None=None, search: str | None=None) -> Page[ActivityTypeResponse]:
    return reference_service.list_activity_types(db, user, page=page, page_size=page_size, active_only=active_only, category=category, search=search)

@router.post('/activity-types', response_model=ActivityTypeResponse, status_code=201)
def create_activity_type(payload: ActivityTypeCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityTypeResponse:
    return reference_service.create_activity_type(db, user, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.patch('/activity-types/{activity_type_id}', response_model=ActivityTypeResponse)
def update_activity_type(activity_type_id: UUID, payload: ActivityTypeUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityTypeResponse:
    return reference_service.update_activity_type(db, user, activity_type_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)
