from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.ports import FacilityRef
from ecotrace.modules.facilities.application.facility_service import get_facility


def require_facility_in_organization(
    db: Session,
    organization_id: uuid.UUID,
    facility_id: uuid.UUID,
) -> FacilityRef:
    facility = get_facility(db, organization_id, facility_id)
    return FacilityRef(
        id=facility.id,
        organization_id=facility.organization_id,
        code=facility.code,
        name=facility.name,
        timezone=facility.timezone,
        is_active=facility.is_active,
    )
