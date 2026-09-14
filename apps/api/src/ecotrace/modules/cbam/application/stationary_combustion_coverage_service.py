from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    get_current_result_ids_for_binding,
    get_stationary_combustion_stale_reason_codes,
)
from ecotrace.modules.cbam.application.stationary_combustion_eligibility import (
    is_eligible_stationary_combustion_activity,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

COVERAGE_MISSING = 'MISSING'
COVERAGE_CURRENT = 'CURRENT'
COVERAGE_STALE = 'STALE'


class StationaryCombustionActivityCoverageItem(CamelModel):
    activity_record_id: uuid.UUID
    activity_date: date | None
    effective_reference_date: date | None
    activity_type: str
    fuel_code: str
    fuel_name: str
    quantity: Decimal
    unit: str
    coverage_status: str
    current_result_id: uuid.UUID | None
    current_run_id: uuid.UUID | None
    current_result_created_at: datetime | None
    current_result_value: Decimal | None
    current_result_unit: str | None
    stale_reason_codes: list[str]
    blocking_issue_codes: list[str]


def _active_fuels_by_code(db: Session) -> dict[str, CbamStationaryCombustionFuel]:
    rows = db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.status == 'ACTIVE'
        )
    ).scalars().all()
    return {row.code: row for row in rows}


def _activity_sort_key(activity: CbamActivityRecord) -> tuple[bool, date, uuid.UUID]:
    # Deterministic: activity_date ascending (nulls last), then stable activity id.
    date_key = activity.activity_date is None, activity.activity_date or date.min
    return (*date_key, activity.id)


def list_stationary_combustion_activity_coverage(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[StationaryCombustionActivityCoverageItem]:
    """
    Authoritative per-activity current/missing/stale coverage for a binding.

    Eligibility, current pointers, and stale detection reuse Phase 5A services.
    Ordering: activity_date ASC (nulls last), activity id ASC.
    """
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    fuels_by_code = _active_fuels_by_code(db)

    activities = list(
        db.execute(
            select(CbamActivityRecord).where(
                CbamActivityRecord.organization_id == organization_id,
                CbamActivityRecord.reporting_period_binding_id == binding_id,
                CbamActivityRecord.status == 'active',
            )
        )
        .scalars()
        .all()
    )
    eligible = [
        a for a in activities if is_eligible_stationary_combustion_activity(a, fuels_by_code)
    ]
    eligible.sort(key=_activity_sort_key)
    total = len(eligible)
    start = max(0, (page - 1) * page_size)
    page_activities = eligible[start : start + page_size]

    pointer_map = get_current_result_ids_for_binding(
        db, organization_id=organization_id, binding_id=binding_id
    )
    page_result_ids = [
        pointer_map[a.id] for a in page_activities if a.id in pointer_map
    ]
    results_by_id: dict[uuid.UUID, CbamStationaryCombustionResult] = {}
    if page_result_ids:
        rows = db.execute(
            select(CbamStationaryCombustionResult).where(
                CbamStationaryCombustionResult.id.in_(page_result_ids),
                CbamStationaryCombustionResult.organization_id == organization_id,
                CbamStationaryCombustionResult.reporting_period_binding_id == binding_id,
            )
        ).scalars().all()
        results_by_id = {row.id: row for row in rows}

    items: list[StationaryCombustionActivityCoverageItem] = []
    for activity in page_activities:
        fuel = fuels_by_code[activity.activity_type]
        pointer_result_id = pointer_map.get(activity.id)
        result = results_by_id.get(pointer_result_id) if pointer_result_id else None

        # Fail closed: missing pointer/result or cross-scope result → MISSING (never CURRENT).
        if (
            pointer_result_id is None
            or result is None
            or result.activity_record_id != activity.id
            or result.organization_id != organization_id
            or result.reporting_period_binding_id != binding_id
        ):
            items.append(
                StationaryCombustionActivityCoverageItem(
                    activity_record_id=activity.id,
                    activity_date=activity.activity_date,
                    effective_reference_date=activity.activity_date,
                    activity_type=activity.activity_type,
                    fuel_code=fuel.code,
                    fuel_name=fuel.name,
                    quantity=activity.quantity,
                    unit=activity.unit,
                    coverage_status=COVERAGE_MISSING,
                    current_result_id=None,
                    current_run_id=None,
                    current_result_created_at=None,
                    current_result_value=None,
                    current_result_unit=None,
                    stale_reason_codes=[],
                    blocking_issue_codes=['MISSING_CALCULATION'],
                )
            )
            continue

        stale_codes = get_stationary_combustion_stale_reason_codes(activity, result)
        if stale_codes:
            status = COVERAGE_STALE
            blocking = list(stale_codes)
        else:
            status = COVERAGE_CURRENT
            blocking = []

        effective_ref = activity.activity_date or result.calculation_reference_date
        items.append(
            StationaryCombustionActivityCoverageItem(
                activity_record_id=activity.id,
                activity_date=activity.activity_date,
                effective_reference_date=effective_ref,
                activity_type=activity.activity_type,
                fuel_code=fuel.code,
                fuel_name=fuel.name,
                quantity=activity.quantity,
                unit=activity.unit,
                coverage_status=status,
                current_result_id=result.id,
                current_run_id=result.calculation_run_id,
                current_result_created_at=result.created_at,
                current_result_value=result.result_value,
                current_result_unit=result.result_unit,
                stale_reason_codes=stale_codes,
                blocking_issue_codes=blocking,
            )
        )

    return paginate(items, page=page, page_size=page_size, total_items=total)
