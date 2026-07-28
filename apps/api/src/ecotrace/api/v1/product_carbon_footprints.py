from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.product_carbon_footprint.application import pcf_service
from ecotrace.modules.product_carbon_footprint.application.pcf_service import FootprintResponse
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Product Carbon Footprints'])

@router.get('/organizations/{organization_id}/product-carbon-footprints', response_model=Page[FootprintResponse])
def list_footprints(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), product_id: UUID | None=Query(None, alias='productId'), status: str | None=None) -> Page[FootprintResponse]:
    return pcf_service.list_footprints(db, user, organization_id, page=page, page_size=page_size, product_id=product_id, status=status)

@router.get('/organizations/{organization_id}/product-carbon-footprints/{footprint_id}', response_model=FootprintResponse)
def get_footprint(organization_id: UUID, footprint_id: UUID, db: DbSession, user: CurrentUser) -> FootprintResponse:
    return pcf_service.get_footprint_detail(db, user, organization_id, footprint_id)

@router.post('/organizations/{organization_id}/product-carbon-footprints/{footprint_id}/approve', response_model=FootprintResponse)
def approve(organization_id: UUID, footprint_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FootprintResponse:
    return pcf_service.approve_footprint(db, user, organization_id, footprint_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/product-carbon-footprints/{footprint_id}/supersede', response_model=FootprintResponse)
def supersede(organization_id: UUID, footprint_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> FootprintResponse:
    return pcf_service.supersede_footprint(db, user, organization_id, footprint_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
