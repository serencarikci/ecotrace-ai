from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.constants import ROLE_ORGANIZATION_ADMIN, ROLE_SYSTEM_ADMIN
from ecotrace.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from ecotrace.modules.identity.application.auth_service import user_has_role
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import (
    Organization,
    OrganizationMembership,
)
from ecotrace.modules.organizations.presentation.schemas import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import Page, paginate


def _to_response(org: Organization) -> OrganizationResponse:
    return OrganizationResponse.model_validate(org)


def user_can_view_organization(db: Session, user: User, organization_id: uuid.UUID) -> bool:
    if user_has_role(user, ROLE_SYSTEM_ADMIN):
        return True
    stmt = select(OrganizationMembership.id).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.is_active.is_(True),
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def user_can_update_organization(db: Session, user: User, organization_id: uuid.UUID) -> bool:
    if user_has_role(user, ROLE_SYSTEM_ADMIN):
        return True
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.is_active.is_(True),
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if membership is None:
        return False
    return membership.role.code == ROLE_ORGANIZATION_ADMIN


def get_organization_or_404(db: Session, organization_id: uuid.UUID) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    return org


def list_organizations(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
) -> Page[OrganizationResponse]:
    offset = (page - 1) * page_size

    if user_has_role(user, ROLE_SYSTEM_ADMIN):
        total = db.execute(select(func.count()).select_from(Organization)).scalar_one()
        stmt = (
            select(Organization).order_by(Organization.name.asc()).offset(offset).limit(page_size)
        )
    else:
        membership_org_ids = (
            select(OrganizationMembership.organization_id)
            .where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.is_active.is_(True),
            )
            .scalar_subquery()
        )
        base = select(Organization).where(Organization.id.in_(membership_org_ids))
        total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        stmt = base.order_by(Organization.name.asc()).offset(offset).limit(page_size)

    orgs = list(db.execute(stmt).scalars().all())
    return paginate(
        [_to_response(o) for o in orgs],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def get_organization_for_user(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
) -> OrganizationResponse:
    if not user_can_view_organization(db, user, organization_id):
        raise NotFoundError("Organization not found.")
    org = get_organization_or_404(db, organization_id)
    return _to_response(org)


def create_organization(
    db: Session,
    user: User,
    payload: OrganizationCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> OrganizationResponse:
    if not user_has_role(user, ROLE_SYSTEM_ADMIN):
        raise AuthorizationError("Only system administrators can create organizations.")

    existing = db.execute(
        select(Organization).where(Organization.slug == payload.slug)
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("An organization with this slug already exists.")

    org = Organization(
        name=payload.name,
        slug=payload.slug,
        legal_name=payload.legal_name,
        country_code=payload.country_code,
        timezone=payload.timezone,
        is_active=payload.is_active,
    )
    db.add(org)
    db.flush()
    write_audit_log(
        db,
        action="organization.create",
        actor_user_id=user.id,
        organization_id=org.id,
        entity_type="organization",
        entity_id=str(org.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"slug": org.slug},
    )
    db.commit()
    db.refresh(org)
    return _to_response(org)


def update_organization(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: OrganizationUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> OrganizationResponse:
    if not user_can_update_organization(db, user, organization_id):
        if not user_can_view_organization(db, user, organization_id):
            raise NotFoundError("Organization not found.")
        raise AuthorizationError("You do not have permission to update this organization.")

    org = get_organization_or_404(db, organization_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(org, key, value)

    write_audit_log(
        db,
        action="organization.update",
        actor_user_id=user.id,
        organization_id=org.id,
        entity_type="organization",
        entity_id=str(org.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(org)
    return _to_response(org)
