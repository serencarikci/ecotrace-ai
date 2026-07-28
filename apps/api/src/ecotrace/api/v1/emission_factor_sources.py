from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.emission_factors.application import source_service
from ecotrace.modules.emission_factors.application.source_service import FactorSourceCreate, FactorSourceResponse, FactorSourceUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(prefix='/emission-factor-sources', tags=['Emission Factor Sources'])

@router.get('', response_model=Page[FactorSourceResponse])
def list_sources(db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), active_only: bool=Query(False, alias='activeOnly'), search: str | None=None) -> Page[FactorSourceResponse]:
    return source_service.list_sources(db, user, page=page, page_size=page_size, active_only=active_only, search=search)

@router.post('', response_model=FactorSourceResponse, status_code=201)
def create_source(payload: FactorSourceCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorSourceResponse:
    return source_service.create_source(db, user, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/{source_id}', response_model=FactorSourceResponse)
def get_source(source_id: UUID, db: DbSession, user: CurrentUser) -> FactorSourceResponse:
    return source_service.get_source(db, user, source_id)

@router.patch('/{source_id}', response_model=FactorSourceResponse)
def update_source(source_id: UUID, payload: FactorSourceUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorSourceResponse:
    return source_service.update_source(db, user, source_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/{source_id}/archive', response_model=FactorSourceResponse)
def archive_source(source_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FactorSourceResponse:
    return source_service.archive_source(db, user, source_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
