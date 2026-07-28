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
from ecotrace.modules.facilities.application import facility_service
from ecotrace.modules.facilities.application.facility_service import (
    FacilityCreate,
    FacilityResponse,
    FacilityUpdate,
)
from ecotrace.shared.domain.schemas import Page

router = APIRouter(tags=["Facilities"])


@router.get(
    "/organizations/{organization_id}/facilities",
    response_model=Page[FacilityResponse],
)
def list_facilities(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    search: str | None = None,
    facility_type: str | None = Query(None, alias="facilityType"),
    country_code: str | None = Query(None, alias="countryCode"),
    city: str | None = None,
    is_active: bool | None = Query(None, alias="isActive"),
) -> Page[FacilityResponse]:
    return facility_service.list_facilities(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        search=search,
        facility_type=facility_type,
        country_code=country_code,
        city=city,
        is_active=is_active,
    )


@router.post(
    "/organizations/{organization_id}/facilities",
    response_model=FacilityResponse,
    status_code=201,
)
def create_facility(
    organization_id: UUID,
    payload: FacilityCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FacilityResponse:
    return facility_service.create_facility(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/facilities/{facility_id}",
    response_model=FacilityResponse,
)
def get_facility(
    organization_id: UUID,
    facility_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> FacilityResponse:
    return facility_service.get_facility_detail(db, user, organization_id, facility_id)


@router.patch(
    "/organizations/{organization_id}/facilities/{facility_id}",
    response_model=FacilityResponse,
)
def update_facility(
    organization_id: UUID,
    facility_id: UUID,
    payload: FacilityUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FacilityResponse:
    return facility_service.update_facility(
        db,
        user,
        organization_id,
        facility_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/facilities/{facility_id}/archive",
    response_model=FacilityResponse,
)
def archive_facility(
    organization_id: UUID,
    facility_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> FacilityResponse:
    return facility_service.archive_facility(
        db,
        user,
        organization_id,
        facility_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
