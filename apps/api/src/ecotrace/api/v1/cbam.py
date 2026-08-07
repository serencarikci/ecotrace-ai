"""CBAM / SKDM API router (Phase 1 foundation).

Prefix: /api/v1/cbam/organizations/{organizationId}/...
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ecotrace.api.dependencies.auth import CurrentUser, DbSession
from ecotrace.modules.cbam.application.module_status_service import (
    CbamModuleStatusResponse,
    get_module_status,
)

router = APIRouter(prefix="/cbam", tags=["CBAM"])


@router.get(
    "/organizations/{organization_id}/module-status",
    response_model=CbamModuleStatusResponse,
    summary="CBAM module foundation status",
    description=(
        "Reports that the CBAM module foundation is registered. "
        "Does not perform calculations, reporting, or compliance assessment."
    ),
)
def cbam_module_status(
    organization_id: UUID,
    db: DbSession,
    user: CurrentUser,
) -> CbamModuleStatusResponse:
    return get_module_status(db, user, organization_id)
