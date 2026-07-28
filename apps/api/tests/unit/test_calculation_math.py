from decimal import Decimal

import pytest

from ecotrace.modules.carbon_accounting.application.calculation_math import (
    calculate_direct_co2e,
    calculate_gas_specific,
    compute_emission_result,
    kg_to_tonnes,
)


def test_direct_factor_calculation_precision() -> None:
    total = calculate_direct_co2e(
        normalized_quantity=Decimal("1000.12345678"),
        factor_value=Decimal("0.442"),
    )
    assert total == Decimal("442.05456790")


def test_kg_to_tonnes_rounding_boundary() -> None:
    assert kg_to_tonnes(Decimal("1234.56789123")) == Decimal("1.234568")


def test_gas_specific_with_gwp() -> None:
    parts = calculate_gas_specific(
        normalized_quantity=Decimal("100"),
        co2_factor=Decimal("2.0"),
        ch4_factor=Decimal("0.001"),
        n2o_factor=Decimal("0.0001"),
        ch4_gwp=Decimal("28"),
        n2o_gwp=Decimal("265"),
    )
    assert parts["co2_kg"] == Decimal("200.00000000")
    assert parts["ch4_kg"] == Decimal("0.10000000")
    assert parts["ch4_kg_co2e"] == Decimal("2.80000000")
    assert parts["n2o_kg_co2e"] == Decimal("2.65000000")
    assert parts["total_kg_co2e"] == Decimal("205.45000000")


def test_biogenic_separated_from_fossil_total() -> None:
    result = compute_emission_result(
        normalized_quantity=Decimal("10"),
        normalized_unit_code="m3",
        factor_value=Decimal("2.0"),
        factor_unit_code="kgCO2e/m3",
        co2_factor=None,
        ch4_factor=None,
        n2o_factor=None,
        biogenic_co2_factor=Decimal("0.5"),
        ch4_gwp=None,
        n2o_gwp=None,
    )
    assert result["total_kg_co2e"] == Decimal("20.00000000")
    assert result["biogenic_co2_kg"] == Decimal("5.00000000")
    assert result["biogenic_co2_kg"] not in (result["total_kg_co2e"],)


def test_negative_quantity_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_direct_co2e(normalized_quantity=Decimal("-1"), factor_value=Decimal("1"))
