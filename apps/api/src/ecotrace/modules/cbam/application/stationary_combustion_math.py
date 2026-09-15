from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any, Literal

from ecotrace.modules.cbam.application.calculation_math import quantize_result
from ecotrace.modules.cbam.application.catalogs import (
    CO2_EF_ENERGY_UNITS,
    MASS_ACTIVITY_UNITS,
    NCV_UNITS,
    VOLUME_ACTIVITY_UNITS,
    density_unit_for_volume,
    kg_to_gg,
    kg_to_tonnes,
    mass_to_kg,
)

CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2 = "STATIONARY_COMBUSTION_CO2_V1"
FORMULA_VERSION_STATIONARY_COMBUSTION_CO2 = "stationary-combustion-co2-v1"
RESULT_UNIT_TCO2 = "tCO2"

InputBasis = Literal["VOLUME", "MASS"]


@dataclass(frozen=True, slots=True)
class ParameterProvenance:
    source_document: str
    source_table: str
    dataset_version: str
    source_reference: str | None = None


@dataclass(frozen=True, slots=True)
class QuantifiedParameter:
    value: Decimal
    unit: str
    provenance: ParameterProvenance


@dataclass(frozen=True, slots=True)
class StationaryCombustionInputs:
    fuel_code: str
    fuel_name: str
    activity_quantity: Decimal
    activity_unit: str
    input_basis: InputBasis
    net_calorific_value: QuantifiedParameter
    co2_emission_factor: QuantifiedParameter
    oxidation_factor: Decimal
    oxidation_factor_provenance: ParameterProvenance
    density: QuantifiedParameter | None = None


@dataclass(frozen=True, slots=True)
class StationaryCombustionDerived:
    fuel_mass_kg: Decimal
    fuel_mass_gg: Decimal
    energy_content_tj: Decimal
    co2_emissions_kg: Decimal
    co2_emissions_tonnes: Decimal


@dataclass(frozen=True, slots=True)
class StationaryCombustionSnapshot:
    calculation_type: str
    formula_version: str
    fuel_code: str
    fuel_name: str
    activity_quantity: str
    activity_unit: str
    input_basis: str
    density_value: str | None
    density_unit: str | None
    density_provenance: dict[str, str | None] | None
    net_calorific_value: str
    net_calorific_value_unit: str
    net_calorific_value_provenance: dict[str, str | None]
    co2_emission_factor: str
    co2_emission_factor_unit: str
    co2_emission_factor_provenance: dict[str, str | None]
    oxidation_factor: str
    oxidation_factor_provenance: dict[str, str | None]
    derived: dict[str, str]
    result_value_quantized: str
    result_unit: str


@dataclass(frozen=True, slots=True)
class StationaryCombustionOutcome:
    ok: bool
    result_value: Decimal | None = None
    result_unit: str | None = None
    derived: StationaryCombustionDerived | None = None
    snapshot: StationaryCombustionSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None


def _fail(code: str, message: str) -> StationaryCombustionOutcome:
    return StationaryCombustionOutcome(ok=False, error_code=code, error_message=message)


def _provenance_dict(provenance: ParameterProvenance) -> dict[str, str | None]:
    return {
        "source_document": provenance.source_document,
        "source_table": provenance.source_table,
        "dataset_version": provenance.dataset_version,
        "source_reference": provenance.source_reference,
    }


def _require_provenance(provenance: ParameterProvenance, *, field: str) -> str | None:
    if not provenance.source_document.strip():
        return f"{field} source_document is required."
    if not provenance.source_table.strip():
        return f"{field} source_table is required."
    if not provenance.dataset_version.strip():
        return f"{field} dataset_version is required."
    return None


def _validate_parameter(
    param: QuantifiedParameter,
    *,
    field: str,
    allowed_units: frozenset[str],
) -> str | None:
    provenance_error = _require_provenance(param.provenance, field=field)
    if provenance_error:
        return provenance_error
    if param.value <= 0:
        return f"{field} must be greater than zero."
    if param.unit not in allowed_units:
        return f"{field} unit {param.unit!r} is incompatible."
    return None


def calculate_stationary_combustion_co2(
    inputs: StationaryCombustionInputs,
) -> StationaryCombustionOutcome:
    if not inputs.fuel_code.strip():
        return _fail("INVALID_INPUT", "fuel_code is required.")
    if not inputs.fuel_name.strip():
        return _fail("INVALID_INPUT", "fuel_name is required.")
    if inputs.activity_quantity < 0:
        return _fail("INVALID_INPUT", "Activity quantity cannot be negative.")

    if inputs.input_basis == "VOLUME":
        if inputs.activity_unit not in VOLUME_ACTIVITY_UNITS:
            return _fail(
                "INCOMPATIBLE_UNIT",
                f"Activity unit {inputs.activity_unit!r} is incompatible with VOLUME basis.",
            )
        if inputs.density is None:
            return _fail(
                "INVALID_INPUT",
                "Density is required when input_basis is VOLUME.",
            )
        expected_density_unit = density_unit_for_volume(inputs.activity_unit)
        density_error = _validate_parameter(
            inputs.density,
            field="density",
            allowed_units=frozenset({expected_density_unit} if expected_density_unit else set()),
        )
        if density_error:
            code = "INCOMPATIBLE_UNIT" if "incompatible" in density_error else "INVALID_INPUT"
            return _fail(code, density_error)
        if expected_density_unit and inputs.density.unit != expected_density_unit:
            return _fail(
                "INCOMPATIBLE_UNIT",
                (
                    f"Density unit {inputs.density.unit!r} is incompatible with "
                    f"activity unit {inputs.activity_unit!r} "
                    f"(expected {expected_density_unit!r})."
                ),
            )
    elif inputs.input_basis == "MASS":
        if inputs.activity_unit not in MASS_ACTIVITY_UNITS:
            return _fail(
                "INCOMPATIBLE_UNIT",
                f"Activity unit {inputs.activity_unit!r} is incompatible with MASS basis.",
            )
        if inputs.density is not None:
            return _fail(
                "INVALID_INPUT",
                "Density must not be supplied when input_basis is MASS.",
            )
    else:
        return _fail("INVALID_INPUT", f"Unsupported input_basis: {inputs.input_basis!r}.")

    ncv_error = _validate_parameter(
        inputs.net_calorific_value,
        field="net_calorific_value",
        allowed_units=NCV_UNITS,
    )
    if ncv_error:
        code = "INCOMPATIBLE_UNIT" if "incompatible" in ncv_error else "INVALID_INPUT"
        return _fail(code, ncv_error)

    ef_error = _validate_parameter(
        inputs.co2_emission_factor,
        field="co2_emission_factor",
        allowed_units=CO2_EF_ENERGY_UNITS,
    )
    if ef_error:
        code = "INCOMPATIBLE_UNIT" if "incompatible" in ef_error else "INVALID_INPUT"
        return _fail(code, ef_error)

    oxidation_prov_error = _require_provenance(
        inputs.oxidation_factor_provenance,
        field="oxidation_factor",
    )
    if oxidation_prov_error:
        return _fail("INVALID_INPUT", oxidation_prov_error)
    if inputs.oxidation_factor < 0:
        return _fail("INVALID_INPUT", "Oxidation factor cannot be negative.")

    if inputs.activity_quantity == 0:
        derived = StationaryCombustionDerived(
            fuel_mass_kg=Decimal("0"),
            fuel_mass_gg=Decimal("0"),
            energy_content_tj=Decimal("0"),
            co2_emissions_kg=Decimal("0"),
            co2_emissions_tonnes=Decimal("0"),
        )
        quantized = quantize_result(derived.co2_emissions_tonnes)
        snapshot = _build_snapshot(inputs, derived, quantized)
        return StationaryCombustionOutcome(
            ok=True,
            result_value=quantized,
            result_unit=RESULT_UNIT_TCO2,
            derived=derived,
            snapshot=snapshot,
        )

    if inputs.input_basis == "VOLUME":
        assert inputs.density is not None
        fuel_mass_kg = inputs.activity_quantity * inputs.density.value
    else:
        converted = mass_to_kg(inputs.activity_quantity, inputs.activity_unit)
        if converted is None:
            return _fail(
                "INCOMPATIBLE_UNIT",
                f"Unable to convert mass unit {inputs.activity_unit!r} to kg.",
            )
        fuel_mass_kg = converted

    fuel_mass_gg = kg_to_gg(fuel_mass_kg)
    energy_content_tj = fuel_mass_gg * inputs.net_calorific_value.value
    co2_emissions_kg = (
        energy_content_tj * inputs.co2_emission_factor.value * inputs.oxidation_factor
    )
    co2_emissions_tonnes = kg_to_tonnes(co2_emissions_kg)

    derived = StationaryCombustionDerived(
        fuel_mass_kg=fuel_mass_kg,
        fuel_mass_gg=fuel_mass_gg,
        energy_content_tj=energy_content_tj,
        co2_emissions_kg=co2_emissions_kg,
        co2_emissions_tonnes=co2_emissions_tonnes,
    )
    quantized = quantize_result(co2_emissions_tonnes)
    snapshot = _build_snapshot(inputs, derived, quantized)
    return StationaryCombustionOutcome(
        ok=True,
        result_value=quantized,
        result_unit=RESULT_UNIT_TCO2,
        derived=derived,
        snapshot=snapshot,
    )


def _build_snapshot(
    inputs: StationaryCombustionInputs,
    derived: StationaryCombustionDerived,
    quantized_result: Decimal,
) -> StationaryCombustionSnapshot:
    density_prov: dict[str, str | None] | None = None
    if inputs.density is not None:
        density_prov = _provenance_dict(inputs.density.provenance)
    return StationaryCombustionSnapshot(
        calculation_type=CALCULATION_TYPE_STATIONARY_COMBUSTION_CO2,
        formula_version=FORMULA_VERSION_STATIONARY_COMBUSTION_CO2,
        fuel_code=inputs.fuel_code,
        fuel_name=inputs.fuel_name,
        activity_quantity=str(inputs.activity_quantity),
        activity_unit=inputs.activity_unit,
        input_basis=inputs.input_basis,
        density_value=str(inputs.density.value) if inputs.density else None,
        density_unit=inputs.density.unit if inputs.density else None,
        density_provenance=density_prov,
        net_calorific_value=str(inputs.net_calorific_value.value),
        net_calorific_value_unit=inputs.net_calorific_value.unit,
        net_calorific_value_provenance=_provenance_dict(inputs.net_calorific_value.provenance),
        co2_emission_factor=str(inputs.co2_emission_factor.value),
        co2_emission_factor_unit=inputs.co2_emission_factor.unit,
        co2_emission_factor_provenance=_provenance_dict(inputs.co2_emission_factor.provenance),
        oxidation_factor=str(inputs.oxidation_factor),
        oxidation_factor_provenance=_provenance_dict(inputs.oxidation_factor_provenance),
        derived={
            "fuel_mass_kg": str(derived.fuel_mass_kg),
            "fuel_mass_gg": str(derived.fuel_mass_gg),
            "energy_content_tj": str(derived.energy_content_tj),
            "co2_emissions_kg": str(derived.co2_emissions_kg),
            "co2_emissions_tonnes": str(derived.co2_emissions_tonnes),
        },
        result_value_quantized=str(quantized_result),
        result_unit=RESULT_UNIT_TCO2,
    )


def snapshot_as_dict(snapshot: StationaryCombustionSnapshot) -> dict[str, Any]:
    return asdict(snapshot)
