from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ecotrace.modules.cbam.application.catalogs import (
    convert_to_canonical,
    get_emission_intensity_parts,
    units_exactly_compatible,
)

RESULT_SCALE = Decimal('0.00000001')
FORMULA_VERSION = 'multiply-activity-by-factor-v1'
CALCULATION_TYPE_MULTIPLY = 'MULTIPLY_ACTIVITY_BY_FACTOR'
ENGINE_VERSION = 'minimal-calculation-v1'


def quantize_result(value: Decimal) -> Decimal:
    return value.quantize(RESULT_SCALE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class MultiplyOutcome:
    ok: bool
    result_value: Decimal | None = None
    result_unit: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def multiply_activity_by_factor(
    *,
    activity_quantity: Decimal,
    activity_unit: str,
    factor_value: Decimal,
    factor_unit: str,
) -> MultiplyOutcome:
    if activity_quantity <= 0:
        return MultiplyOutcome(
            ok=False,
            error_code='INVALID_INPUT',
            error_message='Source quantity must be greater than zero.',
        )
    if factor_value <= 0:
        return MultiplyOutcome(
            ok=False,
            error_code='INVALID_INPUT',
            error_message='Factor value must be greater than zero.',
        )

    parts = get_emission_intensity_parts(factor_unit)
    if parts is None:
        return MultiplyOutcome(
            ok=False,
            error_code='UNSUPPORTED_FORMULA',
            error_message=(
                f'Factor unit {factor_unit!r} is not an explicit intensity unit '
                f'(expected like kgCO2e/kWh).'
            ),
        )
    result_unit, per_unit = parts

    if not units_exactly_compatible(activity_unit, per_unit):
        return MultiplyOutcome(
            ok=False,
            error_code='INCOMPATIBLE_UNIT',
            error_message=(
                f'Source unit {activity_unit!r} is incompatible with factor denominator '
                f'{per_unit!r} (no density/calorific/GWP invent).'
            ),
        )

    activity_canon = convert_to_canonical(activity_quantity, activity_unit)
    per_canon = convert_to_canonical(Decimal('1'), per_unit)
    if activity_canon is None or per_canon is None or per_canon == 0:
        return MultiplyOutcome(
            ok=False,
            error_code='INCOMPATIBLE_UNIT',
            error_message='Unable to normalize source and factor denominator units.',
        )

    activity_in_per_unit = activity_canon / per_canon
    result = quantize_result(activity_in_per_unit * factor_value)
    return MultiplyOutcome(ok=True, result_value=result, result_unit=result_unit)
