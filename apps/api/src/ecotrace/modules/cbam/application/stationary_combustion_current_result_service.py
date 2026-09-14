from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionCurrentResult,
    CbamStationaryCombustionResult,
)


def get_current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    activity_id: uuid.UUID,
) -> CbamStationaryCombustionCurrentResult | None:
    return db.execute(
        select(CbamStationaryCombustionCurrentResult).where(
            CbamStationaryCombustionCurrentResult.organization_id == organization_id,
            CbamStationaryCombustionCurrentResult.reporting_period_binding_id == binding_id,
            CbamStationaryCombustionCurrentResult.activity_record_id == activity_id,
        )
    ).scalar_one_or_none()


def get_current_result_ids_for_binding(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> dict[uuid.UUID, uuid.UUID]:
    """Map activity_record_id -> current_result_id for a binding."""
    rows = db.execute(
        select(
            CbamStationaryCombustionCurrentResult.activity_record_id,
            CbamStationaryCombustionCurrentResult.current_result_id,
        ).where(
            CbamStationaryCombustionCurrentResult.organization_id == organization_id,
            CbamStationaryCombustionCurrentResult.reporting_period_binding_id == binding_id,
        )
    ).all()
    return {activity_id: result_id for activity_id, result_id in rows}


def set_current_result_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    activity_id: uuid.UUID,
    result_id: uuid.UUID,
) -> None:
    """
    Atomically insert/replace the current pointer for an activity.

    Concurrency rule: last successful commit wins. PostgreSQL UNIQUE on
    (organization_id, reporting_period_binding_id, activity_record_id) plus
    ON CONFLICT DO UPDATE keeps exactly one pointer row. Composite FK ensures
    the result belongs to the same org/binding/activity (DB-level).
    """
    now = datetime.now(UTC)
    stmt = (
        pg_insert(CbamStationaryCombustionCurrentResult)
        .values(
            id=uuid.uuid4(),
            organization_id=organization_id,
            reporting_period_binding_id=binding_id,
            activity_record_id=activity_id,
            current_result_id=result_id,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            index_elements=[
                'organization_id',
                'reporting_period_binding_id',
                'activity_record_id',
            ],
            set_={
                'current_result_id': result_id,
                'updated_at': now,
            },
        )
    )
    db.execute(stmt)


def decimals_equal(left: Decimal, right: Decimal) -> bool:
    return left.compare(right) == 0


# Stable codes for coverage / UI mapping (not shown raw to end users).
STALE_REASON_OWNERSHIP_OR_BINDING = 'OWNERSHIP_OR_BINDING_MISMATCH'
STALE_REASON_ACTIVITY_INACTIVE = 'ACTIVITY_INACTIVE'
STALE_REASON_FUEL_TYPE_CHANGED = 'FUEL_TYPE_CHANGED'
STALE_REASON_UNIT_CHANGED = 'UNIT_CHANGED'
STALE_REASON_QUANTITY_CHANGED = 'QUANTITY_CHANGED'
STALE_REASON_DATE_CHANGED = 'DATE_CHANGED'


def get_stationary_combustion_stale_reason_codes(
    activity: CbamActivityRecord,
    result: CbamStationaryCombustionResult,
) -> list[str]:
    """
    Material mismatch reasons between live activity and immutable snapshot.
    Empty list means the current result is still valid for downstream use.
    """
    reasons: list[str] = []
    if (
        activity.organization_id != result.organization_id
        or activity.reporting_period_binding_id != result.reporting_period_binding_id
        or activity.id != result.activity_record_id
    ):
        reasons.append(STALE_REASON_OWNERSHIP_OR_BINDING)
        return reasons
    if activity.status != 'active':
        reasons.append(STALE_REASON_ACTIVITY_INACTIVE)
    if activity.activity_type != result.fuel_code:
        reasons.append(STALE_REASON_FUEL_TYPE_CHANGED)
    if activity.unit != result.activity_unit:
        reasons.append(STALE_REASON_UNIT_CHANGED)
    if not decimals_equal(activity.quantity, result.activity_quantity):
        reasons.append(STALE_REASON_QUANTITY_CHANGED)
    if (
        activity.activity_date is not None
        and (
            result.calculation_reference_date is None
            or activity.activity_date != result.calculation_reference_date
        )
    ):
        reasons.append(STALE_REASON_DATE_CHANGED)
    return reasons


def is_stationary_combustion_result_stale(
    activity: CbamActivityRecord,
    result: CbamStationaryCombustionResult,
) -> bool:
    """
    Snapshot remains historically valid; stale only for current downstream use when
    the live activity material no longer matches the snapshot.
    """
    return bool(get_stationary_combustion_stale_reason_codes(activity, result))
