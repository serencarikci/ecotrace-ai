from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from ecotrace.api.dependencies.auth import (
    ClientIp,
    CurrentUser,
    DbSession,
    RequestId,
    UserAgentHeader,
)
from ecotrace.modules.operational_assets.application import asset_service
from ecotrace.modules.operational_assets.application.asset_service import (
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
)
from ecotrace.shared.application.org_access import ensure_org_access
from ecotrace.shared.domain.schemas import Page

router = APIRouter(tags=["Equipment"])


@router.get(
    "/organizations/{organization_id}/equipment",
    response_model=Page[EquipmentResponse],
)
def list_equipment(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    facility_id: UUID | None = Query(None, alias="facilityId"),
    production_line_id: UUID | None = Query(None, alias="productionLineId"),
    equipment_type: str | None = Query(None, alias="equipmentType"),
    is_active: bool | None = Query(None, alias="isActive"),
    search: str | None = None,
) -> Page[EquipmentResponse]:
    return asset_service.list_equipment(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        facility_id=facility_id,
        production_line_id=production_line_id,
        equipment_type=equipment_type,
        is_active=is_active,
        search=search,
    )


@router.post(
    "/organizations/{organization_id}/equipment",
    response_model=EquipmentResponse,
    status_code=201,
)
def create_equipment(
    organization_id: UUID,
    payload: EquipmentCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> EquipmentResponse:
    return asset_service.create_equipment(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/equipment/{equipment_id}",
    response_model=EquipmentResponse,
)
def get_equipment(
    organization_id: UUID,
    equipment_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> EquipmentResponse:
    ensure_org_access(db, user, organization_id)
    return EquipmentResponse.model_validate(
        asset_service.get_equipment(db, organization_id, equipment_id)
    )


@router.patch(
    "/organizations/{organization_id}/equipment/{equipment_id}",
    response_model=EquipmentResponse,
)
def update_equipment(
    organization_id: UUID,
    equipment_id: UUID,
    payload: EquipmentUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> EquipmentResponse:
    return asset_service.update_equipment(
        db,
        user,
        organization_id,
        equipment_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/equipment/{equipment_id}/archive",
    response_model=EquipmentResponse,
)
def archive_equipment(
    organization_id: UUID,
    equipment_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> EquipmentResponse:
    return asset_service.archive_equipment(
        db,
        user,
        organization_id,
        equipment_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
