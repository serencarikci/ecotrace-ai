"""Purchased-electricity indirect emissions math (Decimal only).

Workbook-authoritative facility formula (SEE D_Processes T66 / SKDM E9 path):

    indirect_emissions_tCO2e = electricity_consumption_MWh × factor_(tCO2e|/tCO2)_per_MWh

Exported electricity is NOT subtracted here (SEE stores export separately as T72).
Product allocation / monthly E/D attribution are out of Phase 8A scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ecotrace.modules.cbam.application.calculation_math import RESULT_SCALE, quantize_result
from ecotrace.modules.cbam.application.catalogs import (
    convert_to_canonical,
    get_emission_intensity_parts,
)
from ecotrace.modules.cbam.application.purchased_electricity_constants import (
    CANONICAL_FACTOR_UNIT,
    ELECTRICITY_FACTOR_UNITS,
    ELECTRICITY_QUANTITY_UNITS,
    RESULT_UNIT,
    ZERO,
)


@dataclass(frozen=True, slots=True)
class ElectricityMathOutcome:
    ok: bool
    electricity_mwh: Decimal | None = None
    factor_tco2e_per_mwh: Decimal | None = None
    indirect_emissions_tco2e: Decimal | None = None
    result_unit: str | None = None
    error_code: str | None = None
    error_message: str | None = None


def to_mwh(quantity: Decimal, unit: str) -> Decimal:
    if unit not in ELECTRICITY_QUANTITY_UNITS:
        raise ValueError('INCOMPATIBLE_ELECTRICITY_UNIT')
    if quantity < ZERO:
        raise ValueError('NEGATIVE_ELECTRICITY_QUANTITY')
    canon_wh = convert_to_canonical(quantity, unit)
    if canon_wh is None:
        raise ValueError('INCOMPATIBLE_ELECTRICITY_UNIT')
    mwh_scale = convert_to_canonical(Decimal('1'), 'MWh')
    assert mwh_scale is not None and mwh_scale != ZERO
    return canon_wh / mwh_scale


def factor_to_tco2e_per_mwh(factor_value: Decimal, factor_unit: str) -> Decimal:
    if factor_unit not in ELECTRICITY_FACTOR_UNITS:
        raise ValueError('INCOMPATIBLE_FACTOR_UNIT')
    if factor_value < ZERO:
        raise ValueError('NEGATIVE_FACTOR_VALUE')
    parts = get_emission_intensity_parts(factor_unit)
    if parts is None:
        raise ValueError('INCOMPATIBLE_FACTOR_UNIT')
    result_unit, per_unit = parts
    # Normalize to tCO2e/MWh numerically. CO2 vs CO2e labels stay distinct in snapshots;
    # stored result_unit is always tCO2e per Phase 8A (workbook E8 / SEE indirect path).
    if result_unit not in {'tCO2e', 'tCO2', 'kgCO2e', 'kgCO2'}:
        raise ValueError('INCOMPATIBLE_FACTOR_UNIT')
    if per_unit not in ELECTRICITY_QUANTITY_UNITS:
        raise ValueError('INCOMPATIBLE_FACTOR_UNIT')

    # Convert factor so that (qty_MWh × factor) yields tonnes-scale CO2e.
    # Start from: emissions_in_result_unit = qty_in_per_unit × factor_value
    # Then convert result mass unit to tonnes and quantity to MWh-equivalent.
    qty_one_mwh_in_per = to_mwh(Decimal('1'), 'MWh') / to_mwh(Decimal('1'), per_unit)
    # emissions in result_unit for 1 MWh:
    emissions_raw = qty_one_mwh_in_per * factor_value
    if result_unit in {'kgCO2e', 'kgCO2'}:
        emissions_tonnes = emissions_raw / Decimal('1000')
    else:
        emissions_tonnes = emissions_raw
    return emissions_tonnes


def calculate_indirect_electricity_emissions(
    *,
    electricity_quantity: Decimal,
    electricity_unit: str,
    factor_value: Decimal,
    factor_unit: str,
) -> ElectricityMathOutcome:
    try:
        mwh = to_mwh(electricity_quantity, electricity_unit)
        factor_mwh = factor_to_tco2e_per_mwh(factor_value, factor_unit)
    except ValueError as exc:
        code = str(exc)
        messages = {
            'INCOMPATIBLE_ELECTRICITY_UNIT': (
                'Electricity quantity unit must be kWh or MWh.'
            ),
            'NEGATIVE_ELECTRICITY_QUANTITY': (
                'Electricity quantity cannot be negative.'
            ),
            'INCOMPATIBLE_FACTOR_UNIT': (
                'Electricity factor unit must be an electricity intensity unit '
                f'(e.g. {CANONICAL_FACTOR_UNIT}).'
            ),
            'NEGATIVE_FACTOR_VALUE': 'Electricity factor cannot be negative.',
        }
        return ElectricityMathOutcome(
            ok=False,
            error_code=code,
            error_message=messages.get(code, 'Invalid electricity calculation input.'),
        )

    raw = mwh * factor_mwh
    result = quantize_result(raw)
    return ElectricityMathOutcome(
        ok=True,
        electricity_mwh=mwh,
        factor_tco2e_per_mwh=factor_mwh,
        indirect_emissions_tco2e=result,
        result_unit=RESULT_UNIT,
    )


def validate_exported_quantity(quantity: Decimal, unit: str) -> Decimal:
    """Validate and normalize exported electricity to MWh; not used in indirect math."""
    return to_mwh(quantity, unit)


# Re-export scale for tests
__all__ = [
    'RESULT_SCALE',
    'ElectricityMathOutcome',
    'calculate_indirect_electricity_emissions',
    'factor_to_tco2e_per_mwh',
    'to_mwh',
    'validate_exported_quantity',
]
