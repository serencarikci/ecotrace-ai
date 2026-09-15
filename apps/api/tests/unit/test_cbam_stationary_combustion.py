from __future__ import annotations

from decimal import Decimal
from typing import Literal

from ecotrace.modules.cbam.application.calculation_math import (
    CALCULATION_TYPE_MULTIPLY,
    CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2,
    multiply_activity_by_factor,
)
from ecotrace.modules.cbam.application.stationary_combustion_math import (
    FORMULA_VERSION_STATIONARY_COMBUSTION_CO2,
    ParameterProvenance,
    QuantifiedParameter,
    StationaryCombustionInputs,
    calculate_stationary_combustion_co2,
)

# Workbook reference values (Excel float heritage). Exact Decimal arithmetic is
# slightly longer; assertions use a tight absolute tolerance.
GOLDEN_ABS_TOL = Decimal("1e-12")

IPCC_NCV = ParameterProvenance(
    source_document="2006 IPCC Guidelines, Volume 2, Chapter 1",
    source_table="Table 1.2",
    dataset_version="2006-IPCC-V2",
    source_reference="Net calorific value — natural gas",
)
IPCC_EF = ParameterProvenance(
    source_document="2006 IPCC Guidelines, Volume 2, Chapter 2",
    source_table="Table 2.3",
    dataset_version="2006-IPCC-V2",
    source_reference="Manufacturing industries and construction — natural gas CO2",
)
OXIDATION_PROV = ParameterProvenance(
    source_document="2006 IPCC Guidelines, Volume 2",
    source_table="Oxidation factor convention",
    dataset_version="2006-IPCC-V2",
    source_reference="Complete oxidation",
)
DENSITY_PROV = ParameterProvenance(
    source_document="Verified stationary-combustion workbook example",
    source_table="Natural gas density fixture",
    dataset_version="fixture-v1",
    source_reference="Example density 0.67 kg/Sm3 (not a global default)",
)

JANUARY_SM3 = Decimal("105437.03007518797")
EXPECTED_JANUARY_MASS_KG = Decimal("70642.81015037594")
EXPECTED_JANUARY_TCO2 = Decimal("190.2269591729323")

MONTHLY_SM3: tuple[Decimal, ...] = (
    Decimal("105437.03007518797"),
    Decimal("101965.03759398496"),
    Decimal("111871.99248120301"),
    Decimal("88821.99248120301"),
    Decimal("108529.04135338345"),
    Decimal("51312.96992481203"),
    Decimal("109129.04135338345"),
    Decimal("94590.97744360902"),
    Decimal("89543"),
    Decimal("94880"),
    Decimal("96586"),
    Decimal("89881"),
)
EXPECTED_ANNUAL_TCO2 = Decimal("2061.3578296655637")


def _assert_close(actual: Decimal, expected: Decimal, *, tol: Decimal = GOLDEN_ABS_TOL) -> None:
    assert abs(actual - expected) <= tol, f"{actual} !≈ {expected} (tol={tol})"


def _natural_gas_inputs(
    *,
    quantity: Decimal,
    unit: str = "Sm3",
    input_basis: Literal["VOLUME", "MASS"] = "VOLUME",
    density_value: Decimal | None = Decimal("0.67"),
    density_unit: str = "kg/Sm3",
    ncv: Decimal = Decimal("48"),
    ncv_unit: str = "TJ/Gg",
    ef: Decimal = Decimal("56100"),
    ef_unit: str = "kgCO2/TJ",
    oxidation: Decimal = Decimal("1"),
    include_density: bool = True,
) -> StationaryCombustionInputs:
    density = None
    if include_density and density_value is not None:
        density = QuantifiedParameter(
            value=density_value,
            unit=density_unit,
            provenance=DENSITY_PROV,
        )
    return StationaryCombustionInputs(
        fuel_code="NATURAL_GAS",
        fuel_name="Natural gas",
        activity_quantity=quantity,
        activity_unit=unit,
        input_basis=input_basis,
        density=density,
        net_calorific_value=QuantifiedParameter(
            value=ncv,
            unit=ncv_unit,
            provenance=IPCC_NCV,
        ),
        co2_emission_factor=QuantifiedParameter(
            value=ef,
            unit=ef_unit,
            provenance=IPCC_EF,
        ),
        oxidation_factor=oxidation,
        oxidation_factor_provenance=OXIDATION_PROV,
    )


def test_golden_january_natural_gas() -> None:
    outcome = calculate_stationary_combustion_co2(_natural_gas_inputs(quantity=JANUARY_SM3))
    assert outcome.ok, outcome.error_message
    assert outcome.derived is not None
    _assert_close(outcome.derived.fuel_mass_kg, EXPECTED_JANUARY_MASS_KG)
    _assert_close(outcome.derived.co2_emissions_tonnes, EXPECTED_JANUARY_TCO2)
    assert outcome.result_unit == "tCO2"
    assert outcome.result_value == outcome.derived.co2_emissions_tonnes.quantize(
        Decimal("0.00000001")
    )
    assert outcome.snapshot is not None
    assert outcome.snapshot.calculation_type == CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2
    assert outcome.snapshot.formula_version == FORMULA_VERSION_STATIONARY_COMBUSTION_CO2
    assert outcome.snapshot.density_value == "0.67"
    assert outcome.snapshot.density_unit == "kg/Sm3"


def test_twelve_month_reconciliation() -> None:
    total = Decimal("0")
    for qty in MONTHLY_SM3:
        outcome = calculate_stationary_combustion_co2(_natural_gas_inputs(quantity=qty))
        assert outcome.ok, outcome.error_message
        assert outcome.derived is not None
        total += outcome.derived.co2_emissions_tonnes
    _assert_close(total, EXPECTED_ANNUAL_TCO2)


def test_zero_consumption() -> None:
    outcome = calculate_stationary_combustion_co2(_natural_gas_inputs(quantity=Decimal("0")))
    assert outcome.ok
    assert outcome.derived is not None
    assert outcome.derived.co2_emissions_tonnes == Decimal("0")
    assert outcome.result_value == Decimal("0.00000000")


def test_negative_consumption() -> None:
    outcome = calculate_stationary_combustion_co2(_natural_gas_inputs(quantity=Decimal("-1")))
    assert not outcome.ok
    assert outcome.error_code == "INVALID_INPUT"


def test_volume_without_density() -> None:
    outcome = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, include_density=False)
    )
    assert not outcome.ok
    assert outcome.error_code == "INVALID_INPUT"
    assert outcome.error_message is not None
    assert "Density" in outcome.error_message


def test_zero_and_negative_density() -> None:
    zero = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, density_value=Decimal("0"))
    )
    assert not zero.ok
    assert zero.error_code == "INVALID_INPUT"

    negative = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, density_value=Decimal("-0.67"))
    )
    assert not negative.ok
    assert negative.error_code == "INVALID_INPUT"


def test_mass_based_kg_input() -> None:
    mass_kg = JANUARY_SM3 * Decimal("0.67")
    outcome = calculate_stationary_combustion_co2(
        _natural_gas_inputs(
            quantity=mass_kg,
            unit="kg",
            input_basis="MASS",
            include_density=False,
        )
    )
    assert outcome.ok, outcome.error_message
    assert outcome.derived is not None
    assert outcome.derived.fuel_mass_kg == mass_kg
    _assert_close(outcome.derived.co2_emissions_tonnes, EXPECTED_JANUARY_TCO2)


def test_mass_based_tonne_input() -> None:
    mass_kg = JANUARY_SM3 * Decimal("0.67")
    mass_t = mass_kg / Decimal("1000")
    outcome = calculate_stationary_combustion_co2(
        _natural_gas_inputs(
            quantity=mass_t,
            unit="t",
            input_basis="MASS",
            include_density=False,
        )
    )
    assert outcome.ok, outcome.error_message
    assert outcome.derived is not None
    assert outcome.derived.fuel_mass_kg == mass_kg
    _assert_close(outcome.derived.co2_emissions_tonnes, EXPECTED_JANUARY_TCO2)


def test_mass_based_gg_input() -> None:
    mass_kg = JANUARY_SM3 * Decimal("0.67")
    mass_gg = mass_kg / Decimal("1000000")
    outcome = calculate_stationary_combustion_co2(
        _natural_gas_inputs(
            quantity=mass_gg,
            unit="Gg",
            input_basis="MASS",
            include_density=False,
        )
    )
    assert outcome.ok, outcome.error_message
    assert outcome.derived is not None
    assert outcome.derived.fuel_mass_kg == mass_kg
    _assert_close(outcome.derived.co2_emissions_tonnes, EXPECTED_JANUARY_TCO2)


def test_missing_or_invalid_ncv() -> None:
    missing_prov = StationaryCombustionInputs(
        fuel_code="NATURAL_GAS",
        fuel_name="Natural gas",
        activity_quantity=JANUARY_SM3,
        activity_unit="Sm3",
        input_basis="VOLUME",
        density=QuantifiedParameter(
            value=Decimal("0.67"),
            unit="kg/Sm3",
            provenance=DENSITY_PROV,
        ),
        net_calorific_value=QuantifiedParameter(
            value=Decimal("48"),
            unit="TJ/Gg",
            provenance=ParameterProvenance(
                source_document="",
                source_table="Table 1.2",
                dataset_version="2006-IPCC-V2",
            ),
        ),
        co2_emission_factor=QuantifiedParameter(
            value=Decimal("56100"),
            unit="kgCO2/TJ",
            provenance=IPCC_EF,
        ),
        oxidation_factor=Decimal("1"),
        oxidation_factor_provenance=OXIDATION_PROV,
    )
    bad_prov = calculate_stationary_combustion_co2(missing_prov)
    assert not bad_prov.ok
    assert bad_prov.error_code == "INVALID_INPUT"

    zero_ncv = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, ncv=Decimal("0"))
    )
    assert not zero_ncv.ok
    assert zero_ncv.error_code == "INVALID_INPUT"

    bad_unit = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, ncv_unit="MJ/kg")
    )
    assert not bad_unit.ok
    assert bad_unit.error_code == "INCOMPATIBLE_UNIT"


def test_missing_or_invalid_co2_factor() -> None:
    zero_ef = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, ef=Decimal("0"))
    )
    assert not zero_ef.ok
    assert zero_ef.error_code == "INVALID_INPUT"

    bad_unit = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, ef_unit="kgCO2e/kWh")
    )
    assert not bad_unit.ok
    assert bad_unit.error_code == "INCOMPATIBLE_UNIT"


def test_invalid_unit_combinations() -> None:
    volume_with_mass_unit = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=Decimal("10"), unit="kg", input_basis="VOLUME")
    )
    assert not volume_with_mass_unit.ok
    assert volume_with_mass_unit.error_code == "INCOMPATIBLE_UNIT"

    mass_with_volume_unit = calculate_stationary_combustion_co2(
        _natural_gas_inputs(
            quantity=Decimal("10"),
            unit="Sm3",
            input_basis="MASS",
            include_density=False,
        )
    )
    assert not mass_with_volume_unit.ok
    assert mass_with_volume_unit.error_code == "INCOMPATIBLE_UNIT"

    density_mismatch = calculate_stationary_combustion_co2(
        _natural_gas_inputs(
            quantity=JANUARY_SM3,
            density_unit="kg/m3",
        )
    )
    assert not density_mismatch.ok
    assert density_mismatch.error_code == "INCOMPATIBLE_UNIT"


def test_oxidation_factor_behavior() -> None:
    half = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, oxidation=Decimal("0.5"))
    )
    assert half.ok
    assert half.derived is not None
    full = calculate_stationary_combustion_co2(_natural_gas_inputs(quantity=JANUARY_SM3))
    assert full.derived is not None
    _assert_close(
        half.derived.co2_emissions_tonnes,
        full.derived.co2_emissions_tonnes * Decimal("0.5"),
    )

    zero_ox = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, oxidation=Decimal("0"))
    )
    assert zero_ox.ok
    assert zero_ox.derived is not None
    assert zero_ox.derived.co2_emissions_tonnes == Decimal("0")

    negative = calculate_stationary_combustion_co2(
        _natural_gas_inputs(quantity=JANUARY_SM3, oxidation=Decimal("-1"))
    )
    assert not negative.ok
    assert negative.error_code == "INVALID_INPUT"


def test_parameter_snapshot_provenance() -> None:
    outcome = calculate_stationary_combustion_co2(_natural_gas_inputs(quantity=JANUARY_SM3))
    assert outcome.ok
    assert outcome.snapshot is not None
    assert outcome.derived is not None
    snap = outcome.snapshot
    assert snap.calculation_type == "STATIONARY_COMBUSTION_CO2_V1"
    assert snap.net_calorific_value == "48"
    assert snap.net_calorific_value_unit == "TJ/Gg"
    assert snap.net_calorific_value_provenance["source_table"] == "Table 1.2"
    assert snap.co2_emission_factor == "56100"
    assert snap.co2_emission_factor_provenance["source_table"] == "Table 2.3"
    assert snap.density_value == "0.67"
    assert snap.density_provenance is not None
    assert "0.67" in (snap.density_provenance["source_reference"] or "")
    assert snap.derived["fuel_mass_kg"] == str(outcome.derived.fuel_mass_kg)
    assert snap.derived["co2_emissions_tonnes"] == str(outcome.derived.co2_emissions_tonnes)
    assert snap.result_unit == "tCO2"


def test_multiply_activity_by_factor_regression() -> None:
    assert CALCULATION_TYPE_MULTIPLY == "MULTIPLY_ACTIVITY_BY_FACTOR"
    assert CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2 != CALCULATION_TYPE_MULTIPLY
    outcome = multiply_activity_by_factor(
        activity_quantity=Decimal("20"),
        activity_unit="MWh",
        factor_value=Decimal("0.4"),
        factor_unit="tCO2e/MWh",
    )
    assert outcome.ok
    assert outcome.result_value == Decimal("8.00000000")
    assert outcome.result_unit == "tCO2e"

    rejected_zero = multiply_activity_by_factor(
        activity_quantity=Decimal("0"),
        activity_unit="MWh",
        factor_value=Decimal("0.4"),
        factor_unit="tCO2e/MWh",
    )
    assert not rejected_zero.ok
    assert rejected_zero.error_code == "INVALID_INPUT"
