from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.constants import (
    ROLE_ANALYST,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_SYSTEM_ADMIN,
    ROLE_VIEWER,
)
from ecotrace.core.exceptions import AuthorizationError, NotFoundError
from ecotrace.modules.identity.application.auth_service import user_has_role
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import OrganizationMembership

_READ_ROLES = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
    ROLE_VIEWER,
    ROLE_SYSTEM_ADMIN,
)
_WRITE_OPS_ROLES = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
    ROLE_SYSTEM_ADMIN,
)
_MANAGER_ROLES = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_SYSTEM_ADMIN,
)
_ADMIN_ROLES = (ROLE_ORGANIZATION_ADMIN, ROLE_SYSTEM_ADMIN)


def ensure_org_access(db: Session, user: User, organization_id: uuid.UUID) -> None:
    if user_has_role(user, ROLE_SYSTEM_ADMIN):
        return
    stmt = select(OrganizationMembership.id).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.is_active.is_(True),
    )
    if db.execute(stmt).scalar_one_or_none() is None:
        raise NotFoundError("Organization not found.")


def membership_role_codes(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    if user_has_role(user, ROLE_SYSTEM_ADMIN):
        return {ROLE_SYSTEM_ADMIN}
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.is_active.is_(True),
    )
    membership = db.execute(stmt).scalar_one_or_none()
    if membership is None:
        raise NotFoundError("Organization not found.")
    codes = {membership.role.code}
    codes.update({role.code for role in user.roles})
    return codes


def require_org_roles(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *allowed: str,
) -> set[str]:
    ensure_org_access(db, user, organization_id)
    codes = membership_role_codes(db, user, organization_id)
    if ROLE_SYSTEM_ADMIN in codes:
        return codes
    if not codes.intersection(allowed):
        raise AuthorizationError("You do not have permission to perform this action.")
    return codes


def require_system_admin(user: User, *, message: str | None = None) -> None:
    if not user_has_role(user, ROLE_SYSTEM_ADMIN):
        raise AuthorizationError(message or "System administrator role required.")


def require_org_read(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_org_roles(db, user, organization_id, *_READ_ROLES)


def require_write_operational(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_org_roles(db, user, organization_id, *_WRITE_OPS_ROLES)


def require_manage_structure(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_org_roles(db, user, organization_id, *_ADMIN_ROLES)


def require_period_manage(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_org_roles(db, user, organization_id, *_MANAGER_ROLES)


def require_period_lock(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_period_manage(db, user, organization_id)


def require_period_unlock(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_org_roles(db, user, organization_id, *_ADMIN_ROLES)


def require_approve(db: Session, user: User, organization_id: uuid.UUID) -> None:
    require_org_roles(db, user, organization_id, *_MANAGER_ROLES)
