from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.ports import ReportingPeriodRef
from ecotrace.modules.reporting_periods.application.period_service import get_period


def require_reporting_period_in_organization(
    db: Session,
    organization_id: uuid.UUID,
    reporting_period_id: uuid.UUID,
) -> ReportingPeriodRef:
    period = get_period(db, organization_id, reporting_period_id)
    return ReportingPeriodRef(
        id=period.id,
        organization_id=period.organization_id,
        code=period.code,
        name=period.name,
        status=period.status,
        start_date=period.start_date,
        end_date=period.end_date,
        period_type=period.period_type,
    )
