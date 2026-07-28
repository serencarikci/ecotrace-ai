from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.operational_assets.application import asset_service
from ecotrace.modules.operational_assets.application.asset_service import DataSourceCreate, DataSourceResponse, DataSourceUpdate
from ecotrace.shared.application.org_access import ensure_org_access
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Data Sources'])

@router.get('/organizations/{organization_id}/data-sources', response_model=Page[DataSourceResponse])
def list_data_sources(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize')) -> Page[DataSourceResponse]:
    return asset_service.list_data_sources(db, user, organization_id, page=page, page_size=page_size)

@router.post('/organizations/{organization_id}/data-sources', response_model=DataSourceResponse, status_code=201)
def create_data_source(organization_id: UUID, payload: DataSourceCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> DataSourceResponse:
    return asset_service.create_data_source(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/data-sources/{data_source_id}', response_model=DataSourceResponse)
def get_data_source(organization_id: UUID, data_source_id: UUID, db: DbSession, user: CurrentUser) -> DataSourceResponse:
    ensure_org_access(db, user, organization_id)
    return asset_service.data_source_response(asset_service.get_data_source(db, organization_id, data_source_id))

@router.patch('/organizations/{organization_id}/data-sources/{data_source_id}', response_model=DataSourceResponse)
def update_data_source(organization_id: UUID, data_source_id: UUID, payload: DataSourceUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> DataSourceResponse:
    return asset_service.update_data_source(db, user, organization_id, data_source_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/data-sources/{data_source_id}/archive', response_model=DataSourceResponse)
def archive_data_source(organization_id: UUID, data_source_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> DataSourceResponse:
    return asset_service.archive_data_source(db, user, organization_id, data_source_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
