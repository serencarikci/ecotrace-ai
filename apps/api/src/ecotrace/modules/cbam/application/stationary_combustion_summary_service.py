from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.calculation_math import quantize_result
from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    get_current_result_ids_for_binding,
    is_stationary_combustion_result_stale,
)
from ecotrace.modules.cbam.application.stationary_combustion_eligibility import (
    is_eligible_stationary_combustion_activity,
)
from ecotrace.modules.cbam.application.stationary_combustion_math import RESULT_UNIT_TCO2
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel

READINESS_EMPTY = 'EMPTY'
READINESS_INCOMPLETE = 'INCOMPLETE'
READINESS_STALE = 'STALE'
READINESS_READY = 'READY'

ZERO = Decimal('0')


class StationaryCombustionFuelTotal(CamelModel):
    fuel_code: str
    fuel_name: str
    activity_count: int
    total_fuel_mass_kg: Decimal
    total_energy_content_tj: Decimal
    total_fossil_co2_tonnes: Decimal
    final_result_value: Decimal
    result_unit: str


class StationaryCombustionPeriodSummaryResponse(CamelModel):
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    period_start: date
    period_end: date
    period_type: str | None
    eligible_activity_count: int
    current_result_count: int
    valid_current_result_count: int
    missing_result_count: int
    stale_result_count: int
    excluded_result_count: int
    is_complete: bool
    readiness_status: str
    blocking_issues: list[str]
    total_fuel_mass_kg: Decimal
    total_fuel_mass_gg: Decimal
    total_energy_content_tj: Decimal
    total_fossil_co2_kg: Decimal
    total_fossil_co2_tonnes: Decimal
    final_result_value: Decimal
    final_result_unit: str
    totals_by_fuel: list[StationaryCombustionFuelTotal]


def _active_fuels_by_code(db: Session) -> dict[str, CbamStationaryCombustionFuel]:
    rows = db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.status == 'ACTIVE'
        )
    ).scalars().all()
    return {row.code: row for row in rows}


def get_stationary_combustion_period_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> StationaryCombustionPeriodSummaryResponse:
    """
    Aggregate only valid current snapshots for the binding.

    Readiness priority when multiple issues exist:
    EMPTY > INCOMPLETE > STALE > READY.
    Blocking issues always list every missing and stale problem found.
    """
    require_cbam_view(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    period = require_reporting_period_in_organization(
        db, organization_id, binding.reporting_period_id
    )
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
    eligible_ids = {a.id for a in eligible}

    current_map = get_current_result_ids_for_binding(
        db, organization_id=organization_id, binding_id=binding_id
    )
    # Only pointers for eligible activities in this binding matter for coverage.
    relevant_pointers = {
        aid: rid for aid, rid in current_map.items() if aid in eligible_ids
    }

    result_ids = list(relevant_pointers.values())
    results_by_id: dict[uuid.UUID, CbamStationaryCombustionResult] = {}
    if result_ids:
        rows = db.execute(
            select(CbamStationaryCombustionResult).where(
                CbamStationaryCombustionResult.id.in_(result_ids),
                CbamStationaryCombustionResult.organization_id == organization_id,
                CbamStationaryCombustionResult.reporting_period_binding_id == binding_id,
            )
        ).scalars().all()
        results_by_id = {row.id: row for row in rows}

    missing_ids: list[uuid.UUID] = []
    stale_ids: list[uuid.UUID] = []
    valid_results: list[CbamStationaryCombustionResult] = []
    excluded = 0

    for activity in eligible:
        pointer_result_id = relevant_pointers.get(activity.id)
        if pointer_result_id is None:
            missing_ids.append(activity.id)
            continue
        result = results_by_id.get(pointer_result_id)
        if result is None:
            missing_ids.append(activity.id)
            excluded += 1
            continue
        if is_stationary_combustion_result_stale(activity, result):
            stale_ids.append(activity.id)
            continue
        valid_results.append(result)

    blocking: list[str] = []
    if missing_ids:
        blocking.append(
            f'{len(missing_ids)} eligible fuel-use record(s) have no current calculation.'
        )
    if stale_ids:
        blocking.append(
            f'{len(stale_ids)} current calculation(s) no longer match their fuel-use record.'
        )

    eligible_count = len(eligible)
    if eligible_count == 0:
        readiness = READINESS_EMPTY
    elif missing_ids:
        readiness = READINESS_INCOMPLETE
    elif stale_ids:
        readiness = READINESS_STALE
    else:
        readiness = READINESS_READY

    total_mass_kg = ZERO
    total_mass_gg = ZERO
    total_energy = ZERO
    total_co2_kg = ZERO
    total_co2_tonnes = ZERO
    by_fuel: dict[str, dict[str, Decimal | int | str]] = defaultdict(
        lambda: {
            'fuel_name': '',
            'activity_count': 0,
            'total_fuel_mass_kg': ZERO,
            'total_energy_content_tj': ZERO,
            'total_fossil_co2_tonnes': ZERO,
        }
    )

    for result in valid_results:
        total_mass_kg += result.fuel_mass_kg
        total_mass_gg += result.fuel_mass_gg
        total_energy += result.energy_content_tj
        total_co2_kg += result.fossil_co2_kg
        total_co2_tonnes += result.fossil_co2_tonnes
        bucket = by_fuel[result.fuel_code]
        bucket['fuel_name'] = result.fuel_name
        bucket['activity_count'] = int(bucket['activity_count']) + 1
        bucket['total_fuel_mass_kg'] = (
            Decimal(str(bucket['total_fuel_mass_kg'])) + result.fuel_mass_kg
        )
        bucket['total_energy_content_tj'] = (
            Decimal(str(bucket['total_energy_content_tj'])) + result.energy_content_tj
        )
        bucket['total_fossil_co2_tonnes'] = (
            Decimal(str(bucket['total_fossil_co2_tonnes'])) + result.fossil_co2_tonnes
        )

    final_total = quantize_result(total_co2_tonnes)
    totals_by_fuel = [
        StationaryCombustionFuelTotal(
            fuel_code=code,
            fuel_name=str(data['fuel_name']),
            activity_count=int(data['activity_count']),
            total_fuel_mass_kg=Decimal(str(data['total_fuel_mass_kg'])),
            total_energy_content_tj=Decimal(str(data['total_energy_content_tj'])),
            total_fossil_co2_tonnes=Decimal(str(data['total_fossil_co2_tonnes'])),
            final_result_value=quantize_result(Decimal(str(data['total_fossil_co2_tonnes']))),
            result_unit=RESULT_UNIT_TCO2,
        )
        for code, data in sorted(by_fuel.items(), key=lambda item: item[0])
    ]

    return StationaryCombustionPeriodSummaryResponse(
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        period_start=period.start_date,
        period_end=period.end_date,
        period_type=period.period_type,
        eligible_activity_count=eligible_count,
        current_result_count=len(relevant_pointers),
        valid_current_result_count=len(valid_results),
        missing_result_count=len(missing_ids),
        stale_result_count=len(stale_ids),
        excluded_result_count=excluded,
        is_complete=readiness == READINESS_READY,
        readiness_status=readiness,
        blocking_issues=blocking,
        total_fuel_mass_kg=total_mass_kg,
        total_fuel_mass_gg=total_mass_gg,
        total_energy_content_tj=total_energy,
        total_fossil_co2_kg=total_co2_kg,
        total_fossil_co2_tonnes=total_co2_tonnes,
        final_result_value=final_total,
        final_result_unit=RESULT_UNIT_TCO2,
        totals_by_fuel=totals_by_fuel,
    )
