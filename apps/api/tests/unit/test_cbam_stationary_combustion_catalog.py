from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ecotrace.core.exceptions import ConflictError, ValidationAppError
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    DATASET_CODE,
    DATASET_VERSION,
    NATURAL_GAS_CODE,
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_service import (
    RESOLUTION_AMBIGUOUS,
    RESOLUTION_RESOLVED,
    RESOLUTION_UNRESOLVED,
    StationaryCombustionFuelCreate,
    StationaryCombustionParameterSetCreate,
    create_fuel,
    create_parameter_set,
    resolve_stationary_combustion_parameters,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamReferenceSource,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionParameterSet,
)


def _ipcc(db):
    return db.execute(
        select(CbamReferenceSource).where(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.code == "IPCC",
        )
    ).scalar_one()


def _param_payload(
    *,
    fuel_id: uuid.UUID,
    ipcc_id: uuid.UUID,
    dataset_version: str,
    valid_from: date,
    valid_until: date | None = None,
    status: str = "ACTIVE",
    ncv: Decimal = Decimal("48"),
    co2: Decimal = Decimal("56100"),
    oxidation: Decimal = Decimal("1"),
    density: Decimal | None = None,
    density_unit: str | None = None,
) -> StationaryCombustionParameterSetCreate:
    return StationaryCombustionParameterSetCreate(
        fuel_id=fuel_id,
        dataset_code="TEST_STATIONARY_COMBUSTION",
        dataset_version=dataset_version,
        valid_from=valid_from,
        valid_until=valid_until,
        status=status,
        net_calorific_value=ncv,
        net_calorific_value_unit="TJ/Gg",
        fossil_co2_emission_factor=co2,
        fossil_co2_emission_factor_unit="kgCO2/TJ",
        oxidation_factor=oxidation,
        reference_density=density,
        reference_density_unit=density_unit,
        ncv_reference_source_id=ipcc_id,
        ncv_source_document="Test NCV document",
        ncv_source_table="Table T-NCV",
        co2_reference_source_id=ipcc_id,
        co2_source_document="Test CO2 document",
        co2_source_table="Table T-CO2",
        oxidation_reference_source_id=ipcc_id,
        oxidation_source_document="Test oxidation document",
        oxidation_source_table="Table T-OX",
    )


def test_natural_gas_seed_values(seeded_db) -> None:
    ensure_platform_stationary_combustion_catalog(seeded_db)
    fuel = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == NATURAL_GAS_CODE
        )
    ).scalar_one()
    assert fuel.name == "Natural Gas"
    assert fuel.input_basis == "VOLUME"
    assert fuel.default_activity_unit == "Sm3"
    assert fuel.status == "ACTIVE"

    param = seeded_db.execute(
        select(CbamStationaryCombustionParameterSet).where(
            CbamStationaryCombustionParameterSet.fuel_id == fuel.id,
            CbamStationaryCombustionParameterSet.dataset_code == DATASET_CODE,
            CbamStationaryCombustionParameterSet.dataset_version == DATASET_VERSION,
        )
    ).scalar_one()
    assert param.net_calorific_value == Decimal("48")
    assert param.net_calorific_value_unit == "TJ/Gg"
    assert param.fossil_co2_emission_factor == Decimal("56100")
    assert param.fossil_co2_emission_factor_unit == "kgCO2/TJ"
    assert param.oxidation_factor == Decimal("1")
    assert param.reference_density is None
    assert param.reference_density_unit is None
    assert param.status == "ACTIVE"


def test_seed_idempotent(seeded_db) -> None:
    ensure_platform_stationary_combustion_catalog(seeded_db)
    ensure_platform_stationary_combustion_catalog(seeded_db)
    fuels = (
        seeded_db.execute(
            select(CbamStationaryCombustionFuel).where(
                CbamStationaryCombustionFuel.code == NATURAL_GAS_CODE
            )
        )
        .scalars()
        .all()
    )
    params = (
        seeded_db.execute(
            select(CbamStationaryCombustionParameterSet).where(
                CbamStationaryCombustionParameterSet.dataset_code == DATASET_CODE,
                CbamStationaryCombustionParameterSet.dataset_version == DATASET_VERSION,
            )
        )
        .scalars()
        .all()
    )
    assert len(fuels) == 1
    assert len(params) == 1


def test_seed_rejects_mutated_published_parameter_version(seeded_db) -> None:
    ensure_platform_stationary_combustion_catalog(seeded_db)
    param = seeded_db.execute(
        select(CbamStationaryCombustionParameterSet).where(
            CbamStationaryCombustionParameterSet.dataset_code == DATASET_CODE,
            CbamStationaryCombustionParameterSet.dataset_version == DATASET_VERSION,
        )
    ).scalar_one()
    original_ncv = param.net_calorific_value
    original_co2 = param.fossil_co2_emission_factor
    param.net_calorific_value = Decimal("47")
    param.fossil_co2_emission_factor = Decimal("56000")
    seeded_db.flush()

    with pytest.raises(ConflictError) as exc_info:
        ensure_platform_stationary_combustion_catalog(seeded_db)
    detail_blob = str(exc_info.value.details)
    assert "IMMUTABLE_PARAMETER_VERSION_CONFLICT" in detail_blob
    assert any(
        d.get("code") == "IMMUTABLE_PARAMETER_VERSION_CONFLICT"
        for d in exc_info.value.details
        if isinstance(d, dict)
    )

    seeded_db.refresh(param)
    assert param.net_calorific_value == Decimal("47")
    assert param.fossil_co2_emission_factor == Decimal("56000")
    # Seed must not rewrite published values back to expected constants either.
    assert param.net_calorific_value != original_ncv
    assert param.fossil_co2_emission_factor != original_co2


def test_inactive_fuel_unresolved(seeded_db) -> None:
    fuel = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == NATURAL_GAS_CODE
        )
    ).scalar_one()
    fuel.status = "INACTIVE"
    seeded_db.flush()
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="NATURAL_GAS",
        reference_date=date(2024, 6, 15),
    )
    assert result.status == RESOLUTION_UNRESOLVED
    assert result.parameters is None


def test_archived_fuel_unresolved(seeded_db) -> None:
    fuel = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == NATURAL_GAS_CODE
        )
    ).scalar_one()
    fuel.status = "ARCHIVED"
    seeded_db.flush()
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="NATURAL_GAS",
        reference_date=date(2024, 6, 15),
    )
    assert result.status == RESOLUTION_UNRESOLVED


def test_inactive_draft_parameter_set_not_resolved_despite_active_fuel(seeded_db) -> None:
    """DRAFT is the non-ACTIVE lifecycle state used instead of INACTIVE for parameter sets."""
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_DRAFT_PARAM",
            name="Test Fuel Draft Param",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
            status="ACTIVE",
        ),
    )
    create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="DRAFT_ONLY",
            valid_from=date(2020, 1, 1),
            status="DRAFT",
        ),
    )
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="TEST_FUEL_DRAFT_PARAM",
        reference_date=date(2024, 1, 1),
    )
    assert result.status == RESOLUTION_UNRESOLVED


def test_archived_parameter_set_not_resolved_despite_active_fuel(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_ARCH_PARAM",
            name="Test Fuel Arch Param",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
            status="ACTIVE",
        ),
    )
    create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="ARCHIVED_V1",
            valid_from=date(2020, 1, 1),
            status="ARCHIVED",
        ),
    )
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="TEST_FUEL_ARCH_PARAM",
        reference_date=date(2024, 1, 1),
    )
    assert result.status == RESOLUTION_UNRESOLVED


def test_resolve_natural_gas_by_valid_date(seeded_db) -> None:
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="NATURAL_GAS",
        reference_date=date(2024, 6, 15),
    )
    assert result.status == RESOLUTION_RESOLVED
    assert result.parameters is not None
    assert result.parameters.fuel_code == "NATURAL_GAS"
    assert result.parameters.net_calorific_value == Decimal("48")
    assert result.parameters.fossil_co2_emission_factor == Decimal("56100")
    assert result.parameters.oxidation_factor == Decimal("1")
    assert result.parameters.reference_density is None
    assert result.parameters.dataset_code == DATASET_CODE
    assert result.parameters.dataset_version == DATASET_VERSION
    assert result.parameters.ncv_provenance.source_table == "Table 1.2"
    assert "Table 2.3" in result.parameters.co2_provenance.source_table


def test_unknown_fuel_unresolved(seeded_db) -> None:
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="UNKNOWN_FUEL",
        reference_date=date(2024, 1, 1),
    )
    assert result.status == RESOLUTION_UNRESOLVED
    assert result.parameters is None


def test_no_applicable_version_unresolved(seeded_db) -> None:
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="NATURAL_GAS",
        reference_date=date(1999, 1, 1),
    )
    assert result.status == RESOLUTION_UNRESOLVED


def test_overlapping_active_rejected_or_ambiguous(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_OVERLAP",
            name="Test Fuel Overlap",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="V1",
            valid_from=date(2020, 1, 1),
            valid_until=None,
        ),
    )
    with pytest.raises(ConflictError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="V2",
                valid_from=date(2021, 1, 1),
                valid_until=None,
            ),
        )

    # Force-insert overlapping ACTIVE rows to verify fail-closed AMBIGUOUS resolution.
    forced = CbamStationaryCombustionParameterSet(
        fuel_id=fuel.id,
        dataset_code="TEST_STATIONARY_COMBUSTION",
        dataset_version="V_FORCED",
        valid_from=date(2022, 1, 1),
        valid_until=None,
        status="ACTIVE",
        net_calorific_value=Decimal("40"),
        net_calorific_value_unit="TJ/Gg",
        fossil_co2_emission_factor=Decimal("50000"),
        fossil_co2_emission_factor_unit="kgCO2/TJ",
        oxidation_factor=Decimal("1"),
        reference_density=None,
        reference_density_unit=None,
        ncv_reference_source_id=ipcc.id,
        ncv_source_document="Forced",
        ncv_source_table="T",
        co2_reference_source_id=ipcc.id,
        co2_source_document="Forced",
        co2_source_table="T",
        oxidation_reference_source_id=ipcc.id,
        oxidation_source_document="Forced",
        oxidation_source_table="T",
    )
    seeded_db.add(forced)
    seeded_db.flush()
    ambiguous = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="TEST_FUEL_OVERLAP",
        reference_date=date(2023, 1, 1),
    )
    assert ambiguous.status == RESOLUTION_AMBIGUOUS
    assert len(ambiguous.candidate_parameter_set_ids) == 2


def test_future_version_does_not_affect_historical_date(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_HISTORY",
            name="Test Fuel History",
            input_basis="MASS",
            default_activity_unit="kg",
        ),
    )
    historical = create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="HIST_V1",
            valid_from=date(2010, 1, 1),
            valid_until=date(2019, 12, 31),
            ncv=Decimal("40"),
        ),
    )
    create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="FUTURE_V2",
            valid_from=date(2020, 1, 1),
            valid_until=None,
            ncv=Decimal("45"),
        ),
    )
    past = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="TEST_FUEL_HISTORY",
        reference_date=date(2015, 6, 1),
    )
    assert past.status == RESOLUTION_RESOLVED
    assert past.parameters is not None
    assert past.parameters.parameter_set_id == historical.id
    assert past.parameters.net_calorific_value == Decimal("40")

    future = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="TEST_FUEL_HISTORY",
        reference_date=date(2024, 1, 1),
    )
    assert future.status == RESOLUTION_RESOLVED
    assert future.parameters is not None
    assert future.parameters.net_calorific_value == Decimal("45")


def test_expired_historical_version_still_resolvable(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_EXPIRED",
            name="Test Fuel Expired",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    expired = create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="OLD_V1",
            valid_from=date(2008, 1, 1),
            valid_until=date(2012, 12, 31),
        ),
    )
    result = resolve_stationary_combustion_parameters(
        seeded_db,
        fuel_code="TEST_FUEL_EXPIRED",
        reference_date=date(2010, 5, 1),
    )
    assert result.status == RESOLUTION_RESOLVED
    assert result.parameters is not None
    assert result.parameters.parameter_set_id == expired.id


def test_invalid_validity_period_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_VALIDITY",
            name="Test Fuel Validity",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="BAD_DATES",
                valid_from=date(2020, 1, 1),
                valid_until=date(2019, 1, 1),
            ),
        )


def test_invalid_ncv_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_NCV",
            name="Test Fuel NCV",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="BAD_NCV",
                valid_from=date(2020, 1, 1),
                ncv=Decimal("0"),
            ),
        )


def test_invalid_co2_factor_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_CO2",
            name="Test Fuel CO2",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="BAD_CO2",
                valid_from=date(2020, 1, 1),
                co2=Decimal("-1"),
            ),
        )


def test_negative_oxidation_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_OX",
            name="Test Fuel OX",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="BAD_OX",
                valid_from=date(2020, 1, 1),
                oxidation=Decimal("-0.1"),
            ),
        )


def test_density_value_without_unit_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_D1",
            name="Test Fuel D1",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="DENSITY_VAL",
                valid_from=date(2020, 1, 1),
                density=Decimal("0.67"),
                density_unit=None,
            ),
        )


def test_density_unit_without_value_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_D2",
            name="Test Fuel D2",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="DENSITY_UNIT",
                valid_from=date(2020, 1, 1),
                density=None,
                density_unit="kg/Sm3",
            ),
        )


def test_non_positive_optional_density_rejected(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_D3",
            name="Test Fuel D3",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    with pytest.raises(ValidationAppError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="DENSITY_ZERO",
                valid_from=date(2020, 1, 1),
                density=Decimal("0"),
                density_unit="kg/Sm3",
            ),
        )


def test_dataset_version_uniqueness(seeded_db) -> None:
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="TEST_FUEL_UNIQUE",
            name="Test Fuel Unique",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    create_parameter_set(
        seeded_db,
        _param_payload(
            fuel_id=fuel.id,
            ipcc_id=ipcc.id,
            dataset_version="SAME_V",
            valid_from=date(2020, 1, 1),
            valid_until=date(2020, 12, 31),
            status="DRAFT",
        ),
    )
    with pytest.raises(ConflictError):
        create_parameter_set(
            seeded_db,
            _param_payload(
                fuel_id=fuel.id,
                ipcc_id=ipcc.id,
                dataset_version="SAME_V",
                valid_from=date(2021, 1, 1),
                valid_until=date(2021, 12, 31),
                status="DRAFT",
            ),
        )
    # DB unique constraint also enforces uniqueness if service is bypassed.
    seeded_db.add(
        CbamStationaryCombustionParameterSet(
            fuel_id=fuel.id,
            dataset_code="TEST_STATIONARY_COMBUSTION",
            dataset_version="SAME_V",
            valid_from=date(2022, 1, 1),
            valid_until=None,
            status="DRAFT",
            net_calorific_value=Decimal("48"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("56100"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="X",
            ncv_source_table="X",
            co2_reference_source_id=ipcc.id,
            co2_source_document="X",
            co2_source_table="X",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="X",
            oxidation_source_table="X",
        )
    )
    with pytest.raises(IntegrityError):
        seeded_db.flush()
    seeded_db.rollback()
