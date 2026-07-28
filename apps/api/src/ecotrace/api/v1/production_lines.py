from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.operational_assets.application import asset_service
from ecotrace.modules.operational_assets.application.asset_service import ProductionLineCreate, ProductionLineResponse, ProductionLineUpdate
from ecotrace.shared.application.org_access import ensure_org_access
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Production Lines'])

@router.get('/organizations/{organization_id}/facilities/{facility_id}/production-lines', response_model=Page[ProductionLineResponse])
def list_production_lines(organization_id: UUID, facility_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize')) -> Page[ProductionLineResponse]:
    return asset_service.list_production_lines(db, user, organization_id, facility_id, page=page, page_size=page_size)

@router.post('/organizations/{organization_id}/facilities/{facility_id}/production-lines', response_model=ProductionLineResponse, status_code=201)
def create_production_line(organization_id: UUID, facility_id: UUID, payload: ProductionLineCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ProductionLineResponse:
    return asset_service.create_production_line(db, user, organization_id, facility_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/production-lines/{production_line_id}', response_model=ProductionLineResponse)
def get_production_line(organization_id: UUID, production_line_id: UUID, db: DbSession, user: CurrentUser) -> ProductionLineResponse:
    ensure_org_access(db, user, organization_id)
    return ProductionLineResponse.model_validate(asset_service.get_production_line(db, organization_id, production_line_id))

@router.patch('/organizations/{organization_id}/production-lines/{production_line_id}', response_model=ProductionLineResponse)
def update_production_line(organization_id: UUID, production_line_id: UUID, payload: ProductionLineUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ProductionLineResponse:
    return asset_service.update_production_line(db, user, organization_id, production_line_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/production-lines/{production_line_id}/archive', response_model=ProductionLineResponse)
def archive_production_line(organization_id: UUID, production_line_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ProductionLineResponse:
    return asset_service.archive_production_line(db, user, organization_id, production_line_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
