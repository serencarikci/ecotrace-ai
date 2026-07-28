from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.suppliers.application import supplier_service
from ecotrace.modules.suppliers.application.supplier_service import SupplierCreate, SupplierResponse, SupplierUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Suppliers'])

@router.get('/organizations/{organization_id}/suppliers', response_model=Page[SupplierResponse])
def list_suppliers(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), search: str | None=None, status: str | None=None, country_code: str | None=Query(None, alias='countryCode')) -> Page[SupplierResponse]:
    return supplier_service.list_suppliers(db, user, organization_id, page=page, page_size=page_size, search=search, status=status, country_code=country_code)

@router.post('/organizations/{organization_id}/suppliers', response_model=SupplierResponse, status_code=201)
def create_supplier(organization_id: UUID, payload: SupplierCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> SupplierResponse:
    return supplier_service.create_supplier(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/suppliers/{supplier_id}', response_model=SupplierResponse)
def get_supplier(organization_id: UUID, supplier_id: UUID, db: DbSession, user: CurrentUser) -> SupplierResponse:
    return supplier_service.get_supplier_detail(db, user, organization_id, supplier_id)

@router.patch('/organizations/{organization_id}/suppliers/{supplier_id}', response_model=SupplierResponse)
def update_supplier(organization_id: UUID, supplier_id: UUID, payload: SupplierUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> SupplierResponse:
    return supplier_service.update_supplier(db, user, organization_id, supplier_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/suppliers/{supplier_id}/archive', response_model=SupplierResponse)
def archive_supplier(organization_id: UUID, supplier_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> SupplierResponse:
    return supplier_service.archive_supplier(db, user, organization_id, supplier_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
