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
    "CBAM/SKDM MVP through Phase 7 audit is available for domain-expert validation. "
    "Exports use an internal development workbook template and Phase 5 calculation "
    "results. Official CBAM workbook mapping remains BLOCKED. "
    "Automatic IPCC/DEFRA/EPA import, GWP invent, CN, shipment, certificate/financial "
    "liability, evidence upload, approve/lock, and official regulatory submission are "
    "not implemented. No compliance claim is made. "
    "Classification: READY_FOR_DOMAIN_VALIDATION (not production/regulatory ready)."
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
