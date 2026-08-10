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

CBAM_ENFORCED_PERMISSIONS: Final[tuple[str, ...]] = (CBAM_VIEW, CBAM_CONFIGURE)

_VIEW_ROLES: Final[tuple[str, ...]] = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_ANALYST,
    ROLE_VIEWER,
    ROLE_SYSTEM_ADMIN,
)
_CONFIGURE_ROLES: Final[tuple[str, ...]] = (
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_SYSTEM_ADMIN,
)


def require_cbam_view(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_org_roles(db, user, organization_id, *_VIEW_ROLES)


def require_cbam_configure(db: Session, user: User, organization_id: uuid.UUID) -> set[str]:
    return require_org_roles(db, user, organization_id, *_CONFIGURE_ROLES)
