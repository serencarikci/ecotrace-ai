from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.products.application import product_service
from ecotrace.modules.products.application.product_service import BatchCreate, BatchResponse, BatchTransition, BatchUpdate, BomCreate, BomResponse, BomUpdate, ProductCreate, ProductResponse, ProductUpdate, VariantCreate, VariantResponse, VariantUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Products'])

@router.get('/organizations/{organization_id}/products', response_model=Page[ProductResponse])
def list_products(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), search: str | None=None, product_type: str | None=Query(None, alias='productType'), product_category: str | None=Query(None, alias='productCategory'), is_active: bool | None=Query(None, alias='isActive')) -> Page[ProductResponse]:
    return product_service.list_products(db, user, organization_id, page=page, page_size=page_size, search=search, product_type=product_type, product_category=product_category, is_active=is_active)

@router.post('/organizations/{organization_id}/products', response_model=ProductResponse, status_code=201)
def create_product(organization_id: UUID, payload: ProductCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ProductResponse:
    return product_service.create_product(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/products/{product_id}', response_model=ProductResponse)
def get_product(organization_id: UUID, product_id: UUID, db: DbSession, user: CurrentUser) -> ProductResponse:
    return product_service.get_product_detail(db, user, organization_id, product_id)

@router.patch('/organizations/{organization_id}/products/{product_id}', response_model=ProductResponse)
def update_product(organization_id: UUID, product_id: UUID, payload: ProductUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ProductResponse:
    return product_service.update_product(db, user, organization_id, product_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/products/{product_id}/archive', response_model=ProductResponse)
def archive_product(organization_id: UUID, product_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ProductResponse:
    return product_service.archive_product(db, user, organization_id, product_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/products/{product_id}/variants', response_model=list[VariantResponse])
def list_variants(organization_id: UUID, product_id: UUID, db: DbSession, user: CurrentUser) -> list[VariantResponse]:
    return product_service.list_variants(db, user, organization_id, product_id)

@router.post('/organizations/{organization_id}/products/{product_id}/variants', response_model=VariantResponse, status_code=201)
def create_variant(organization_id: UUID, product_id: UUID, payload: VariantCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> VariantResponse:
    return product_service.create_variant(db, user, organization_id, product_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/product-variants/{variant_id}', response_model=VariantResponse)
def get_variant(organization_id: UUID, variant_id: UUID, db: DbSession, user: CurrentUser) -> VariantResponse:
    return product_service.get_variant_detail(db, user, organization_id, variant_id)

@router.patch('/organizations/{organization_id}/product-variants/{variant_id}', response_model=VariantResponse)
def update_variant(organization_id: UUID, variant_id: UUID, payload: VariantUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> VariantResponse:
    return product_service.update_variant(db, user, organization_id, variant_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/product-variants/{variant_id}/archive', response_model=VariantResponse)
def archive_variant(organization_id: UUID, variant_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> VariantResponse:
    return product_service.archive_variant(db, user, organization_id, variant_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/product-batches', response_model=Page[BatchResponse])
def list_batches(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), product_id: UUID | None=Query(None, alias='productId'), status: str | None=None, search: str | None=None) -> Page[BatchResponse]:
    return product_service.list_batches(db, user, organization_id, page=page, page_size=page_size, product_id=product_id, status=status, search=search)

@router.post('/organizations/{organization_id}/product-batches', response_model=BatchResponse, status_code=201)
def create_batch(organization_id: UUID, payload: BatchCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BatchResponse:
    return product_service.create_batch(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/product-batches/{batch_id}', response_model=BatchResponse)
def get_batch(organization_id: UUID, batch_id: UUID, db: DbSession, user: CurrentUser) -> BatchResponse:
    return product_service.get_batch_detail(db, user, organization_id, batch_id)

@router.patch('/organizations/{organization_id}/product-batches/{batch_id}', response_model=BatchResponse)
def update_batch(organization_id: UUID, batch_id: UUID, payload: BatchUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BatchResponse:
    return product_service.update_batch(db, user, organization_id, batch_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/product-batches/{batch_id}/transition', response_model=BatchResponse)
def transition_batch(organization_id: UUID, batch_id: UUID, payload: BatchTransition, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BatchResponse:
    return product_service.transition_batch(db, user, organization_id, batch_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/products/{product_id}/boms', response_model=list[BomResponse])
def list_boms(organization_id: UUID, product_id: UUID, db: DbSession, user: CurrentUser) -> list[BomResponse]:
    return product_service.list_boms(db, user, organization_id, product_id)

@router.post('/organizations/{organization_id}/products/{product_id}/boms', response_model=BomResponse, status_code=201)
def create_bom(organization_id: UUID, product_id: UUID, payload: BomCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BomResponse:
    return product_service.create_bom(db, user, organization_id, product_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/boms/{bom_id}', response_model=BomResponse)
def get_bom(organization_id: UUID, bom_id: UUID, db: DbSession, user: CurrentUser) -> BomResponse:
    return product_service.get_bom_detail(db, user, organization_id, bom_id)

@router.patch('/organizations/{organization_id}/boms/{bom_id}', response_model=BomResponse)
def update_bom(organization_id: UUID, bom_id: UUID, payload: BomUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BomResponse:
    return product_service.update_bom(db, user, organization_id, bom_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/boms/{bom_id}/submit-review', response_model=BomResponse)
def submit_bom(organization_id: UUID, bom_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BomResponse:
    return product_service.submit_bom_review(db, user, organization_id, bom_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/boms/{bom_id}/approve', response_model=BomResponse)
def approve_bom(organization_id: UUID, bom_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BomResponse:
    return product_service.approve_bom(db, user, organization_id, bom_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/boms/{bom_id}/clone-version', response_model=BomResponse, status_code=201)
def clone_bom(organization_id: UUID, bom_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BomResponse:
    return product_service.clone_bom_version(db, user, organization_id, bom_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/boms/{bom_id}/archive', response_model=BomResponse)
def archive_bom(organization_id: UUID, bom_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> BomResponse:
    return product_service.archive_bom(db, user, organization_id, bom_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
