from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Query
from ecotrace.api.dependencies.auth import ClientIp, CurrentUser, DbSession, RequestId, UserAgentHeader
from ecotrace.modules.organizations.application import organization_service
from ecotrace.modules.organizations.presentation.schemas import OrganizationCreate, OrganizationResponse, OrganizationUpdate
from ecotrace.shared.domain.schemas import Page
router = APIRouter(prefix='/organizations', tags=['Organizations'])

@router.get('', response_model=Page[OrganizationResponse], summary='List organizations', description='List organizations visible to the current user. System administrators see all; others see memberships only.')
def list_organizations(db: DbSession, user: CurrentUser, page: int=Query(default=1, ge=1), page_size: int=Query(default=20, ge=1, le=100, alias='pageSize')) -> Page[OrganizationResponse]:
    return organization_service.list_organizations(db, user, page=page, page_size=page_size)

@router.get('/{organization_id}', response_model=OrganizationResponse, summary='Get organization')
def get_organization(organization_id: UUID, db: DbSession, user: CurrentUser) -> OrganizationResponse:
    return organization_service.get_organization_for_user(db, user, organization_id)

@router.post('', response_model=OrganizationResponse, status_code=201, summary='Create organization', description='Create an organization. Restricted to system administrators.')
def create_organization(payload: OrganizationCreate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> OrganizationResponse:
    return organization_service.create_organization(db, user, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)

@router.patch('/{organization_id}', response_model=OrganizationResponse, summary='Update organization', description='Update an organization. System admin or organization admin only.')
def update_organization(organization_id: UUID, payload: OrganizationUpdate, db: DbSession, user: CurrentUser, request_id: RequestId, ip: ClientIp, user_agent: UserAgentHeader) -> OrganizationResponse:
    return organization_service.update_organization(db, user, organization_id, payload, request_id=request_id, ip_address=ip, user_agent=user_agent)
