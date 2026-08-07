"""CBAM permission vocabulary and organization-scoped authorization helpers.

Permission strings are a CBAM vocabulary for future phases. Enforcement today
uses existing EcoTrace role codes via ``require_org_roles`` (no separate
permission store). Baseline role mapping follows docs/cbam/workflows.md.

Unresolved (do not invent):
- D-019 declarant / CBAM-specific business roles
- D-038 verifier authorization
"""

from __future__ import annotations

import uuid
from typing import Final

from sqlalchemy.orm import Session

from ecotrace.core.constants import (
    ROLE_ANALYST,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_SYSTEM_ADMIN,
    ROLE_VIEWER,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.org_access import require_org_roles

# Capability vocabulary (colon-delimited capability codes).
CBAM_VIEW: Final[str] = "cbam:view"
CBAM_CONFIGURE: Final[str] = "cbam:configure"
CBAM_DATA_WRITE: Final[str] = "cbam:data:write"
CBAM_DATA_REVIEW: Final[str] = "cbam:data:review"
CBAM_CALCULATE: Final[str] = "cbam:calculate"
CBAM_APPROVE: Final[str] = "cbam:approve"
CBAM_LOCK: Final[str] = "cbam:lock"
CBAM_REPORT: Final[str] = "cbam:report"
CBAM_EVIDENCE_VIEW: Final[str] = "cbam:evidence:view"
CBAM_EVIDENCE_WRITE: Final[str] = "cbam:evidence:write"
CBAM_AUDIT_VIEW: Final[str] = "cbam:audit:view"

CBAM_PERMISSION_VOCABULARY: Final[tuple[str, ...]] = (
    CBAM_VIEW,
    CBAM_CONFIGURE,
    CBAM_DATA_WRITE,
    CBAM_DATA_REVIEW,
    CBAM_CALCULATE,
    CBAM_APPROVE,
    CBAM_LOCK,
    CBAM_REPORT,
    CBAM_EVIDENCE_VIEW,
    CBAM_EVIDENCE_WRITE,
    CBAM_AUDIT_VIEW,
)

_READ_ROLES: Final[tuple[str, ...]] = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
    ROLE_VIEWER,
    ROLE_SYSTEM_ADMIN,
)
_WRITE_OPS_ROLES: Final[tuple[str, ...]] = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
    ROLE_SYSTEM_ADMIN,
)
_MANAGER_ROLES: Final[tuple[str, ...]] = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_SYSTEM_ADMIN,
)
_ADMIN_ROLES: Final[tuple[str, ...]] = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SYSTEM_ADMIN,
)

# Safe baseline mapping to existing roles only (workflows.md). No declarant/verifier.
CBAM_PERMISSION_ROLE_MAP: Final[dict[str, tuple[str, ...]]] = {
    CBAM_VIEW: _READ_ROLES,
    CBAM_CONFIGURE: _MANAGER_ROLES,
    CBAM_DATA_WRITE: _WRITE_OPS_ROLES,
    CBAM_DATA_REVIEW: _MANAGER_ROLES,
    CBAM_CALCULATE: _WRITE_OPS_ROLES,
    CBAM_APPROVE: _MANAGER_ROLES,
    CBAM_LOCK: _MANAGER_ROLES,
    CBAM_REPORT: _MANAGER_ROLES,
    CBAM_EVIDENCE_VIEW: _READ_ROLES,
    CBAM_EVIDENCE_WRITE: _WRITE_OPS_ROLES,
    CBAM_AUDIT_VIEW: _MANAGER_ROLES,
}


def require_cbam_permission(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    permission: str,
) -> set[str]:
    """Verify org membership (404 non-disclosure) then CBAM capability roles."""
    allowed = CBAM_PERMISSION_ROLE_MAP.get(permission)
    if allowed is None:
        raise ValueError(f"Unknown CBAM permission: {permission}")
    return require_org_roles(db, user, organization_id, *allowed)


def require_cbam_view(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_VIEW)


def require_cbam_configure(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_CONFIGURE)


def require_cbam_data_write(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_DATA_WRITE)


def require_cbam_data_review(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_DATA_REVIEW)


def require_cbam_calculate(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_CALCULATE)


def require_cbam_approve(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_APPROVE)


def require_cbam_lock(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_LOCK)


def require_cbam_report(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_REPORT)


def require_cbam_evidence_view(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_EVIDENCE_VIEW)


def require_cbam_evidence_write(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_EVIDENCE_WRITE)


def require_cbam_audit_view(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_cbam_permission(db, user, organization_id, CBAM_AUDIT_VIEW)


# Unlock uses admin roles (workflows.md); not a separate vocabulary code yet.
def require_cbam_unlock(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_org_roles(db, user, organization_id, *_ADMIN_ROLES)
