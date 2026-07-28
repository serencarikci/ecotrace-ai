from __future__ import annotations
from typing import Any
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.carbon_inventory.application import inventory_service
from ecotrace.modules.carbon_inventory.application.inventory_service import MatchPreviewRequest
from ecotrace.modules.emission_factors.application import preference_service
from ecotrace.modules.emission_factors.application.preference_service import PreferenceCreate, PreferenceResponse, PreferenceUpdate
router = APIRouter(prefix='/organizations/{organization_id}', tags=['Carbon Accounting'])

@router.get('/emission-factor-preferences', response_model=list[PreferenceResponse])
def list_preferences(organization_id: UUID, db: DbSession, user: CurrentUser, active_only: bool=Query(True, alias='activeOnly')) -> list[PreferenceResponse]:
    return preference_service.list_preferences(db, user, organization_id, active_only=active_only)

@router.post('/emission-factor-preferences', response_model=PreferenceResponse, status_code=201)
def create_preference(organization_id: UUID, payload: PreferenceCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PreferenceResponse:
    return preference_service.create_preference(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.patch('/emission-factor-preferences/{preference_id}', response_model=PreferenceResponse)
def update_preference(organization_id: UUID, preference_id: UUID, payload: PreferenceUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PreferenceResponse:
    return preference_service.update_preference(db, user, organization_id, preference_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.delete('/emission-factor-preferences/{preference_id}', response_model=PreferenceResponse)
def delete_preference(organization_id: UUID, preference_id: UUID, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> PreferenceResponse:
    return preference_service.delete_preference(db, user, organization_id, preference_id, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.post('/factor-matching/preview')
def preview_match(organization_id: UUID, payload: MatchPreviewRequest, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    return inventory_service.preview_factor_match(db, user, organization_id, payload)
