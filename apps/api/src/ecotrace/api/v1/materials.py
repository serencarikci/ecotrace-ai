from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.materials.application import material_service
from ecotrace.modules.materials.application.material_service import MaterialCreate, MaterialResponse, MaterialUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Materials'])

@router.get('/organizations/{organization_id}/materials', response_model=Page[MaterialResponse])
def list_materials(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), search: str | None=None, material_category: str | None=Query(None, alias='materialCategory'), is_active: bool | None=Query(None, alias='isActive')) -> Page[MaterialResponse]:
    return material_service.list_materials(db, user, organization_id, page=page, page_size=page_size, search=search, material_category=material_category, is_active=is_active)

@router.post('/organizations/{organization_id}/materials', response_model=MaterialResponse, status_code=201)
def create_material(organization_id: UUID, payload: MaterialCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> MaterialResponse:
    return material_service.create_material(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/materials/{material_id}', response_model=MaterialResponse)
def get_material(organization_id: UUID, material_id: UUID, db: DbSession, user: CurrentUser) -> MaterialResponse:
    return material_service.get_material_detail(db, user, organization_id, material_id)

@router.patch('/organizations/{organization_id}/materials/{material_id}', response_model=MaterialResponse)
def update_material(organization_id: UUID, material_id: UUID, payload: MaterialUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> MaterialResponse:
    return material_service.update_material(db, user, organization_id, material_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/materials/{material_id}/archive', response_model=MaterialResponse)
def archive_material(organization_id: UUID, material_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> MaterialResponse:
    return material_service.archive_material(db, user, organization_id, material_id, request_id=request_id, ip_address=ip, user_agent=user_agent)
