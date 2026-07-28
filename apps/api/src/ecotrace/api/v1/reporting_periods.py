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
from ecotrace.modules.reporting_periods.application import period_service
from ecotrace.modules.reporting_periods.application.period_service import (
    PeriodCreate,
    PeriodResponse,
    PeriodUpdate,
)
from ecotrace.shared.application.org_access import ensure_org_access
from ecotrace.shared.domain.schemas import Page

router = APIRouter(tags=["Reporting Periods"])


@router.get(
    "/organizations/{organization_id}/reporting-periods",
    response_model=Page[PeriodResponse],
)
def list_periods(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
) -> Page[PeriodResponse]:
    return period_service.list_periods(db, user, organization_id, page=page, page_size=page_size)


@router.post(
    "/organizations/{organization_id}/reporting-periods",
    response_model=PeriodResponse,
    status_code=201,
)
def create_period(
    organization_id: UUID,
    payload: PeriodCreate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodResponse:
    return period_service.create_period(
        db,
        user,
        organization_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/organizations/{organization_id}/reporting-periods/{period_id}",
    response_model=PeriodResponse,
)
def get_period(
    organization_id: UUID, period_id: UUID, db: DbSession, user: CurrentUser
) -> PeriodResponse:
    ensure_org_access(db, user, organization_id)
    period = period_service.get_period(db, organization_id, period_id)
    resp = PeriodResponse.model_validate(period)
    from sqlalchemy import func, select

    from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord

    count = db.execute(
        select(func.count())
        .select_from(ActivityRecord)
        .where(ActivityRecord.reporting_period_id == period.id)
    ).scalar_one()
    resp.activity_record_count = int(count)
    return resp


@router.patch(
    "/organizations/{organization_id}/reporting-periods/{period_id}",
    response_model=PeriodResponse,
)
def update_period(
    organization_id: UUID,
    period_id: UUID,
    payload: PeriodUpdate,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodResponse:
    return period_service.update_period(
        db,
        user,
        organization_id,
        period_id,
        payload,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-periods/{period_id}/lock",
    response_model=PeriodResponse,
)
def lock_period(
    organization_id: UUID,
    period_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodResponse:
    return period_service.lock_period(
        db,
        user,
        organization_id,
        period_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-periods/{period_id}/unlock",
    response_model=PeriodResponse,
)
def unlock_period(
    organization_id: UUID,
    period_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodResponse:
    return period_service.unlock_period(
        db,
        user,
        organization_id,
        period_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/organizations/{organization_id}/reporting-periods/{period_id}/archive",
    response_model=PeriodResponse,
)
def archive_period(
    organization_id: UUID,
    period_id: UUID,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> PeriodResponse:
    return period_service.archive_period(
        db,
        user,
        organization_id,
        period_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )
