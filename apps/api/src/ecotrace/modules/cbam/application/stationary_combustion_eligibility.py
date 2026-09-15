from __future__ import annotations

from ecotrace.modules.cbam.application.catalogs import (
    MASS_ACTIVITY_UNITS,
    VOLUME_ACTIVITY_UNITS,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionFuel,
)

# Activity types that share codes with stationary-combustion fuels (execution + summary).
ELIGIBLE_STATIONARY_COMBUSTION_ACTIVITY_TYPES = frozenset(
    {
        "NATURAL_GAS",
        "DIESEL",
        "GASOLINE",
        "LPG",
        "OTHER_FUEL",
    }
)


def is_unit_compatible_with_input_basis(*, input_basis: str, activity_unit: str) -> bool:
    if input_basis == "VOLUME":
        return activity_unit in VOLUME_ACTIVITY_UNITS
    if input_basis == "MASS":
        return activity_unit in MASS_ACTIVITY_UNITS
    return False


def is_eligible_stationary_combustion_activity(
    activity: CbamActivityRecord,
    fuels_by_code: dict[str, CbamStationaryCombustionFuel],
) -> bool:
    if activity.status != "active":
        return False
    if activity.activity_type not in ELIGIBLE_STATIONARY_COMBUSTION_ACTIVITY_TYPES:
        return False
    fuel = fuels_by_code.get(activity.activity_type)
    if fuel is None or fuel.status != "ACTIVE":
        return False
    return is_unit_compatible_with_input_basis(
        input_basis=fuel.input_basis,
        activity_unit=activity.unit,
    )
