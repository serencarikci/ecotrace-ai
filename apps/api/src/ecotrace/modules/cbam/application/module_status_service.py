from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ecotrace.modules.cbam import MODULE_CODE, MODULE_UI_LABEL_TR
from ecotrace.modules.cbam.application.permissions import (
    CBAM_ENFORCED_PERMISSIONS,
    require_cbam_view,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel

FOUNDATION_MESSAGE = (
    "SKDM tools are ready for visual review. You can enter period data, run calculations, "
    "and download Internal Excel or Official Excel when the period is ready. "
    "Official Excel is for review only — it is not a legal CBAM submission. "
    "Certificate and tax liability, evidence upload, and formal approve/lock are still limited. "
    "No compliance claim is made."
)


class CbamModuleStatusResponse(CamelModel):
    module: str
    ui_label_tr: str
    status: str
    foundation_available: bool
    domain_functionality_implemented: bool
    compliance_claim: bool
    calculation_implemented: bool
    reporting_implemented: bool
    message: str
    enforced_permissions: list[str]


def get_module_status(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
) -> CbamModuleStatusResponse:
    require_cbam_view(db, user, organization_id)
    return CbamModuleStatusResponse(
        module=MODULE_CODE,
        ui_label_tr=MODULE_UI_LABEL_TR,
        status="mvp_ready_for_domain_validation",
        foundation_available=True,
        domain_functionality_implemented=True,
        compliance_claim=False,
        calculation_implemented=True,
        reporting_implemented=True,
        message=FOUNDATION_MESSAGE,
        enforced_permissions=list(CBAM_ENFORCED_PERMISSIONS),
    )
