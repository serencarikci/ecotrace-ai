from __future__ import annotations
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.activity_data.application import activity_service
from ecotrace.modules.activity_data.application.activity_service import ActivityCreate, ActivityResponse, ActivityUpdate, CorrectRequest, ReasonRequest, RevisionResponse
from ecotrace.shared.application.org_access import ensure_org_access
from ecotrace.shared.domain.schemas import Page
router = APIRouter(tags=['Activity Records'])

@router.get('/organizations/{organization_id}/activity-records', response_model=Page[ActivityResponse])
def list_activity_records(organization_id: UUID, db: DbSession, user: CurrentUser, page: int=Query(1, ge=1), page_size: int=Query(20, ge=1, le=100, alias='pageSize'), facility_id: UUID | None=Query(None, alias='facilityId'), activity_type_id: UUID | None=Query(None, alias='activityTypeId'), reporting_period_id: UUID | None=Query(None, alias='reportingPeriodId'), status: str | None=None, date_from: date | None=Query(None, alias='dateFrom'), date_to: date | None=Query(None, alias='dateTo'), search: str | None=None, sort_by: str=Query('createdAt', alias='sortBy'), sort_direction: str=Query('desc', alias='sortDirection')) -> Page[ActivityResponse]:
    return activity_service.list_records(db, user, organization_id, page=page, page_size=page_size, facility_id=facility_id, activity_type_id=activity_type_id, reporting_period_id=reporting_period_id, status=status, date_from=date_from, date_to=date_to, search=search, sort_by=sort_by, sort_direction=sort_direction)

@router.post('/organizations/{organization_id}/activity-records', response_model=ActivityResponse, status_code=201)
def create_activity_record(organization_id: UUID, payload: ActivityCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.create_record(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/activity-records/{activity_record_id}', response_model=ActivityResponse)
def get_activity_record(organization_id: UUID, activity_record_id: UUID, db: DbSession, user: CurrentUser) -> ActivityResponse:
    ensure_org_access(db, user, organization_id)
    return ActivityResponse.model_validate(activity_service.get_record(db, organization_id, activity_record_id))

@router.patch('/organizations/{organization_id}/activity-records/{activity_record_id}', response_model=ActivityResponse)
def update_activity_record(organization_id: UUID, activity_record_id: UUID, payload: ActivityUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.update_record(db, user, organization_id, activity_record_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/activity-records/{activity_record_id}/submit', response_model=ActivityResponse)
def submit_activity_record(organization_id: UUID, activity_record_id: UUID, payload: ReasonRequest, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.submit_record(db, user, organization_id, activity_record_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/activity-records/{activity_record_id}/approve', response_model=ActivityResponse)
def approve_activity_record(organization_id: UUID, activity_record_id: UUID, payload: ReasonRequest, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.approve_record(db, user, organization_id, activity_record_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/activity-records/{activity_record_id}/reject', response_model=ActivityResponse)
def reject_activity_record(organization_id: UUID, activity_record_id: UUID, payload: ReasonRequest, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.reject_record(db, user, organization_id, activity_record_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/activity-records/{activity_record_id}/correct', response_model=ActivityResponse)
def correct_activity_record(organization_id: UUID, activity_record_id: UUID, payload: CorrectRequest, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.correct_record(db, user, organization_id, activity_record_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/organizations/{organization_id}/activity-records/{activity_record_id}/archive', response_model=ActivityResponse)
def archive_activity_record(organization_id: UUID, activity_record_id: UUID, payload: ReasonRequest, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> ActivityResponse:
    return activity_service.archive_record(db, user, organization_id, activity_record_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.get('/organizations/{organization_id}/activity-records/{activity_record_id}/revisions', response_model=list[RevisionResponse])
def list_revisions(organization_id: UUID, activity_record_id: UUID, db: DbSession, user: CurrentUser) -> list[RevisionResponse]:
    return activity_service.list_revisions(db, user, organization_id, activity_record_id)
