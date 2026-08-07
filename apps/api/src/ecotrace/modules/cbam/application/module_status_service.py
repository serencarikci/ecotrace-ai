"""Phase 1 CBAM module-status capability (no domain behavior)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ecotrace.modules.cbam import MODULE_CODE, MODULE_UI_LABEL_TR
from ecotrace.modules.cbam.application.permissions import (
    CBAM_PERMISSION_VOCABULARY,
    require_cbam_view,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel

FOUNDATION_MESSAGE = (
    "CBAM module foundation is available. CBAM domain functionality is not "
    "implemented yet. No compliance claim is made."
)


class CbamModuleStatusResponse(CamelModel):
    module: str
    ui_label_tr: str
    status: str
    foundation_available: bool
    domain_functionality_implemented: bool
    compliance_claim: bool
    calculation_implemented: bool
    message: str
    permissions_defined: list[str]


def get_module_status(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
) -> CbamModuleStatusResponse:
    require_cbam_view(db, user, organization_id)
    return CbamModuleStatusResponse(
        module=MODULE_CODE,
        ui_label_tr=MODULE_UI_LABEL_TR,
        status="foundation_available",
        foundation_available=True,
        domain_functionality_implemented=False,
        compliance_claim=False,
        calculation_implemented=False,
        message=FOUNDATION_MESSAGE,
        permissions_defined=list(CBAM_PERMISSION_VOCABULARY),
    )
