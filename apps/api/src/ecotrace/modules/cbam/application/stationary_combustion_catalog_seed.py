from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import ConflictError
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.infrastructure.models import (
    CbamReferenceSource,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionParameterSet,
)

NATURAL_GAS_FUEL_ID = uuid.UUID("c2000000-0000-4000-8000-000000000001")
NATURAL_GAS_PARAM_SET_ID = uuid.UUID("c2000000-0000-4000-8000-000000000002")

NATURAL_GAS_CODE = "NATURAL_GAS"
NATURAL_GAS_NAME = "Natural Gas"
NATURAL_GAS_INPUT_BASIS = "VOLUME"
NATURAL_GAS_DEFAULT_UNIT = "Sm3"

DATASET_CODE = "IPCC_2006_STATIONARY_COMBUSTION"
DATASET_VERSION = "2006_V1"

EXPECTED_NCV = Decimal("48")
EXPECTED_NCV_UNIT = "TJ/Gg"
EXPECTED_CO2 = Decimal("56100")
EXPECTED_CO2_UNIT = "kgCO2/TJ"
EXPECTED_OXIDATION = Decimal("1")
EXPECTED_VALID_FROM = date(2006, 1, 1)

NCV_SOURCE_DOCUMENT = (
    "2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2, Chapter 1"
)
NCV_SOURCE_TABLE = "Table 1.2"
CO2_SOURCE_DOCUMENT = (
    "2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2, Chapter 2"
)
CO2_SOURCE_TABLE = "Table 2.3, Manufacturing Industries and Construction"
OXIDATION_SOURCE_DOCUMENT = "2006 IPCC Guidelines for National Greenhouse Gas Inventories, Volume 2"
OXIDATION_SOURCE_TABLE = "Oxidation factor convention (complete oxidation)"


def _assert_fuel_matches_seed(fuel: CbamStationaryCombustionFuel) -> None:
    mismatches: list[dict[str, str]] = []
    expected = {
        "name": NATURAL_GAS_NAME,
        "input_basis": NATURAL_GAS_INPUT_BASIS,
        "default_activity_unit": NATURAL_GAS_DEFAULT_UNIT,
    }
    actual = {
        "name": fuel.name,
        "input_basis": fuel.input_basis,
        "default_activity_unit": fuel.default_activity_unit,
    }
    for field, expected_value in expected.items():
        if actual[field] != expected_value:
            mismatches.append(
                {
                    "field": field,
                    "expected": expected_value,
                    "actual": str(actual[field]),
                }
            )
    if mismatches:
        raise ConflictError(
            "Published stationary-combustion fuel definition conflicts with seed "
            f"for code {NATURAL_GAS_CODE}.",
            details=[{"code": "IMMUTABLE_FUEL_CONFLICT", "mismatches": mismatches}],
        )


def _assert_parameter_set_matches_seed(
    row: CbamStationaryCombustionParameterSet,
    *,
    ipcc_id: uuid.UUID,
) -> None:
    mismatches: list[dict[str, str]] = []
    expected: dict[str, object] = {
        "dataset_code": DATASET_CODE,
        "dataset_version": DATASET_VERSION,
        "valid_from": EXPECTED_VALID_FROM,
        "valid_until": None,
        "status": "ACTIVE",
        "net_calorific_value": EXPECTED_NCV,
        "net_calorific_value_unit": EXPECTED_NCV_UNIT,
        "fossil_co2_emission_factor": EXPECTED_CO2,
        "fossil_co2_emission_factor_unit": EXPECTED_CO2_UNIT,
        "oxidation_factor": EXPECTED_OXIDATION,
        "reference_density": None,
        "reference_density_unit": None,
        "ncv_reference_source_id": ipcc_id,
        "ncv_source_document": NCV_SOURCE_DOCUMENT,
        "ncv_source_table": NCV_SOURCE_TABLE,
        "co2_reference_source_id": ipcc_id,
        "co2_source_document": CO2_SOURCE_DOCUMENT,
        "co2_source_table": CO2_SOURCE_TABLE,
        "oxidation_reference_source_id": ipcc_id,
        "oxidation_source_document": OXIDATION_SOURCE_DOCUMENT,
        "oxidation_source_table": OXIDATION_SOURCE_TABLE,
    }
    for field, expected_value in expected.items():
        actual_value = getattr(row, field)
        if actual_value != expected_value:
            mismatches.append(
                {
                    "field": field,
                    "expected": str(expected_value),
                    "actual": str(actual_value),
                }
            )
    if mismatches:
        raise ConflictError(
            "Published stationary-combustion parameter version conflicts with seed "
            f"({DATASET_CODE}/{DATASET_VERSION}). In-place mutation is not allowed; "
            "create a new dataset_version instead.",
            details=[
                {
                    "code": "IMMUTABLE_PARAMETER_VERSION_CONFLICT",
                    "parameterSetId": str(row.id),
                    "datasetCode": DATASET_CODE,
                    "datasetVersion": DATASET_VERSION,
                    "mismatches": mismatches,
                }
            ],
        )


def ensure_platform_stationary_combustion_catalog(db: Session) -> None:
    ensure_platform_factor_catalog(db)
    ipcc = db.execute(
        select(CbamReferenceSource).where(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.code == "IPCC",
        )
    ).scalar_one()

    fuel = db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == NATURAL_GAS_CODE
        )
    ).scalar_one_or_none()
    if fuel is None:
        fuel = CbamStationaryCombustionFuel(
            id=NATURAL_GAS_FUEL_ID,
            code=NATURAL_GAS_CODE,
            name=NATURAL_GAS_NAME,
            input_basis=NATURAL_GAS_INPUT_BASIS,
            default_activity_unit=NATURAL_GAS_DEFAULT_UNIT,
            status="ACTIVE",
            description=(
                "Platform stationary-combustion fuel definition. "
                "No authoritative default density is seeded."
            ),
        )
        db.add(fuel)
        db.flush()
    else:
        _assert_fuel_matches_seed(fuel)

    existing = db.execute(
        select(CbamStationaryCombustionParameterSet).where(
            CbamStationaryCombustionParameterSet.fuel_id == fuel.id,
            CbamStationaryCombustionParameterSet.dataset_code == DATASET_CODE,
            CbamStationaryCombustionParameterSet.dataset_version == DATASET_VERSION,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            CbamStationaryCombustionParameterSet(
                id=NATURAL_GAS_PARAM_SET_ID,
                fuel_id=fuel.id,
                dataset_code=DATASET_CODE,
                dataset_version=DATASET_VERSION,
                valid_from=EXPECTED_VALID_FROM,
                valid_until=None,
                status="ACTIVE",
                net_calorific_value=EXPECTED_NCV,
                net_calorific_value_unit=EXPECTED_NCV_UNIT,
                fossil_co2_emission_factor=EXPECTED_CO2,
                fossil_co2_emission_factor_unit=EXPECTED_CO2_UNIT,
                oxidation_factor=EXPECTED_OXIDATION,
                reference_density=None,
                reference_density_unit=None,
                ncv_reference_source_id=ipcc.id,
                ncv_source_document=NCV_SOURCE_DOCUMENT,
                ncv_source_table=NCV_SOURCE_TABLE,
                co2_reference_source_id=ipcc.id,
                co2_source_document=CO2_SOURCE_DOCUMENT,
                co2_source_table=CO2_SOURCE_TABLE,
                oxidation_reference_source_id=ipcc.id,
                oxidation_source_document=OXIDATION_SOURCE_DOCUMENT,
                oxidation_source_table=OXIDATION_SOURCE_TABLE,
                notes=(
                    "Density is intentionally null. Workbooks disagree (0.67 vs 0.68 kg/Sm3); "
                    "VOLUME calculations require an explicit density parameter."
                ),
            )
        )
    else:
        _assert_parameter_set_matches_seed(existing, ipcc_id=ipcc.id)
    db.flush()
