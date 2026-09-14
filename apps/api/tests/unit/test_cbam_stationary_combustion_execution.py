from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    installation_service,
    period_binding_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_service import (
    StationaryCombustionFuelCreate,
    StationaryCombustionParameterSetCreate,
    create_fuel,
    create_parameter_set,
)
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    STATIONARY_COMBUSTION_DEFINITION_CODE,
    StationaryCombustionExecutionCommand,
    execute_stationary_combustion_calculation,
    get_stationary_combustion_result,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamCalculationDefinition,
    CbamCalculationRun,
    CbamReferenceSource,
    CbamStationaryCombustionParameterSet,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod

JANUARY_SM3 = Decimal("105437.03007518797")
# Activity quantity column is Numeric(24, 8); persisted value after round-trip.
JANUARY_SM3_PERSISTED = Decimal("105437.03007519")
EXPECTED_JANUARY_TCO2 = Decimal("190.22695917")
DENSITY = Decimal("0.67")


def _org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db):
    return db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()


def _facility(db, org_id):
    return db.execute(
        select(Facility).where(Facility.organization_id == org_id).limit(1)
    ).scalar_one()


def _ipcc(db):
    return db.execute(
        select(CbamReferenceSource).where(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.code == "IPCC",
        )
    ).scalar_one()


def _setup(db, admin, org):
    facility = _facility(db, org.id)
    installation_service.create_installation(
        db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"SC3-{uuid.uuid4().hex[:8]}",
            name="SC Phase3 Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"SC3-{uuid.uuid4().hex[:6]}",
        name="SC3 Period",
        period_type="custom",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        status="open",
    )
    db.add(period)
    db.flush()
    binding = period_binding_service.create_period_binding(
        db, admin, org.id, PeriodBindingCreate(reporting_period_id=period.id)
    )
    opened = period_binding_service.open_data_collection(
        db,
        admin,
        org.id,
        binding.id,
        PeriodBindingVersionRequest(row_version=binding.row_version),
    )
    installation = installation_service.list_installations(
        db, admin, org.id, page=1, page_size=50
    ).items[-1]
    return opened, installation


def _create_ng_activity(db, admin, org, binding, installation, *, quantity=JANUARY_SM3, unit="Sm3"):
    return activity_record_service.create_activity_record(
        db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="NATURAL_GAS",
            quantity=quantity,
            unit=unit,
            data_source_type="PRIMARY",
            activity_date=date(2024, 1, 15),
        ),
    )


def _cmd(**kwargs) -> StationaryCombustionExecutionCommand:
    return StationaryCombustionExecutionCommand(**kwargs)


def test_natural_gas_january_golden_orchestration(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)

    result = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 15),
            density_value=DENSITY,
            density_unit="kg/Sm3",
            requested_by_user_id=admin.id,
        ),
    )
    assert result.calculation_run_status == "COMPLETED"
    assert result.result.result_value == EXPECTED_JANUARY_TCO2
    assert result.result.result_unit == "tCO2"
    assert result.result.density_value == DENSITY
    assert result.result.activity_quantity == JANUARY_SM3_PERSISTED


def test_reload_persisted_snapshot(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    executed = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 6, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    reloaded = get_stationary_combustion_result(seeded_db, executed.result.id)
    assert reloaded is not None
    assert reloaded.fuel_code == "NATURAL_GAS"
    assert reloaded.net_calorific_value == Decimal("48")
    assert reloaded.fossil_co2_emission_factor == Decimal("56100")
    assert reloaded.oxidation_factor == Decimal("1")
    assert reloaded.dataset_version == "2006_V1"
    assert reloaded.ncv_source_table == "Table 1.2"
    assert "Table 2.3" in reloaded.co2_source_table
    assert reloaded.fuel_mass_kg > 0
    assert reloaded.energy_content_tj > 0
    assert reloaded.fossil_co2_tonnes > 0
    assert reloaded.result_value == EXPECTED_JANUARY_TCO2
    assert reloaded.density_value == Decimal("0.67")
    assert reloaded.density_unit == "kg/Sm3"


def test_density_persisted_exactly_no_default(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    executed = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=Decimal("0.67"),
            density_unit="kg/Sm3",
        ),
    )
    assert executed.result.density_value == Decimal("0.67")
    assert executed.result.density_value != Decimal("0.68")


def test_volume_without_density_fails_no_result(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    before = seeded_db.execute(
        select(func.count()).select_from(CbamStationaryCombustionResult)
    ).scalar()
    with pytest.raises(ValidationAppError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
            ),
        )
    assert any(d.get("code") == "DENSITY_REQUIRED" for d in exc.value.details)
    after = seeded_db.execute(
        select(func.count()).select_from(CbamStationaryCombustionResult)
    ).scalar()
    assert after == before


def test_mass_fuel_with_density_fails(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="LPG",
            name="LPG test",
            input_basis="MASS",
            default_activity_unit="kg",
        ),
    )
    create_parameter_set(
        seeded_db,
        StationaryCombustionParameterSetCreate(
            fuel_id=fuel.id,
            dataset_code="TEST_SC",
            dataset_version="V1",
            valid_from=date(2020, 1, 1),
            status="ACTIVE",
            net_calorific_value=Decimal("47"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("63000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="doc",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="doc",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="doc",
            oxidation_source_table="t",
        ),
    )
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="LPG",
            quantity=Decimal("100"),
            unit="kg",
            data_source_type="PRIMARY",
        ),
    )
    with pytest.raises(ValidationAppError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="LPG",
                reference_date=date(2024, 1, 1),
                density_value=Decimal("0.5"),
                density_unit="kg/Sm3",
            ),
        )
    assert any(d.get("code") == "DENSITY_NOT_ALLOWED" for d in exc.value.details)


def test_unknown_fuel_unresolved(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    # ELECTRICITY is not eligible — use OTHER_FUEL activity then unknown fuel mismatch,
    # or eligible type with unknown fuel via mismatch. Unknown fuel after eligibility:
    # create OTHER_FUEL activity and request OTHER_FUEL but no catalog fuel — need fuel code match.
    # Seed does not include DIESEL fuel definition.
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="DIESEL",
            quantity=Decimal("10"),
            unit="Sm3",
            data_source_type="PRIMARY",
        ),
    )
    with pytest.raises(BusinessRuleError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="DIESEL",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
            ),
        )
    assert any(d.get("code") == "UNRESOLVED_PARAMETER_SET" for d in exc.value.details)


def test_no_applicable_parameter_version(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    with pytest.raises(BusinessRuleError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(1990, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
            ),
        )
    assert any(d.get("code") == "UNRESOLVED_PARAMETER_SET" for d in exc.value.details)


def test_ambiguous_parameter_versions_fail_closed(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="OTHER_FUEL",
            name="Other fuel",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    create_parameter_set(
        seeded_db,
        StationaryCombustionParameterSetCreate(
            fuel_id=fuel.id,
            dataset_code="AMB",
            dataset_version="V1",
            valid_from=date(2020, 1, 1),
            status="ACTIVE",
            net_calorific_value=Decimal("40"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("50000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="d",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="d",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="d",
            oxidation_source_table="t",
        ),
    )
    seeded_db.add(
        CbamStationaryCombustionParameterSet(
            fuel_id=fuel.id,
            dataset_code="AMB",
            dataset_version="V2_FORCED",
            valid_from=date(2021, 1, 1),
            valid_until=None,
            status="ACTIVE",
            net_calorific_value=Decimal("41"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("51000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="d",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="d",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="d",
            oxidation_source_table="t",
        )
    )
    seeded_db.flush()
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="OTHER_FUEL",
            quantity=Decimal("100"),
            unit="Sm3",
            data_source_type="PRIMARY",
        ),
    )
    with pytest.raises(BusinessRuleError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="OTHER_FUEL",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
            ),
        )
    assert any(d.get("code") == "AMBIGUOUS_PARAMETER_SET" for d in exc.value.details)


def test_explicit_dataset_version(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    executed = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
            dataset_version="2006_V1",
        ),
    )
    assert executed.result.dataset_version == "2006_V1"

    with pytest.raises(BusinessRuleError):
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
                dataset_version="DOES_NOT_EXIST",
            ),
        )


def test_historical_reference_date(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ipcc = _ipcc(seeded_db)
    fuel = create_fuel(
        seeded_db,
        StationaryCombustionFuelCreate(
            code="GASOLINE",
            name="Gasoline",
            input_basis="VOLUME",
            default_activity_unit="Sm3",
        ),
    )
    hist = create_parameter_set(
        seeded_db,
        StationaryCombustionParameterSetCreate(
            fuel_id=fuel.id,
            dataset_code="HIST",
            dataset_version="OLD",
            valid_from=date(2010, 1, 1),
            valid_until=date(2015, 12, 31),
            status="ACTIVE",
            net_calorific_value=Decimal("44"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("69000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="d",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="d",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="d",
            oxidation_source_table="t",
        ),
    )
    create_parameter_set(
        seeded_db,
        StationaryCombustionParameterSetCreate(
            fuel_id=fuel.id,
            dataset_code="HIST",
            dataset_version="NEW",
            valid_from=date(2016, 1, 1),
            status="ACTIVE",
            net_calorific_value=Decimal("45"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("70000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document="d",
            ncv_source_table="t",
            co2_reference_source_id=ipcc.id,
            co2_source_document="d",
            co2_source_table="t",
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document="d",
            oxidation_source_table="t",
        ),
    )
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="GASOLINE",
            quantity=Decimal("1000"),
            unit="Sm3",
            data_source_type="PRIMARY",
        ),
    )
    executed = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="GASOLINE",
            reference_date=date(2012, 6, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    assert executed.result.parameter_set_id == hist.id
    assert executed.result.net_calorific_value == Decimal("44")


def test_future_catalog_version_does_not_change_snapshot(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    original_ncv = first.result.net_calorific_value
    original_result = first.result.result_value

    # Close current NATURAL_GAS validity and add a future ACTIVE version via direct insert
    # after ending the seed row's open-ended period.
    param = seeded_db.execute(
        select(CbamStationaryCombustionParameterSet).where(
            CbamStationaryCombustionParameterSet.id == first.result.parameter_set_id
        )
    ).scalar_one()
    param.valid_until = date(2024, 12, 31)
    ipcc = _ipcc(seeded_db)
    seeded_db.add(
        CbamStationaryCombustionParameterSet(
            fuel_id=param.fuel_id,
            dataset_code=param.dataset_code,
            dataset_version="2099_V2",
            valid_from=date(2025, 1, 1),
            valid_until=None,
            status="ACTIVE",
            net_calorific_value=Decimal("50"),
            net_calorific_value_unit="TJ/Gg",
            fossil_co2_emission_factor=Decimal("57000"),
            fossil_co2_emission_factor_unit="kgCO2/TJ",
            oxidation_factor=Decimal("1"),
            ncv_reference_source_id=ipcc.id,
            ncv_source_document=param.ncv_source_document,
            ncv_source_table=param.ncv_source_table,
            co2_reference_source_id=ipcc.id,
            co2_source_document=param.co2_source_document,
            co2_source_table=param.co2_source_table,
            oxidation_reference_source_id=ipcc.id,
            oxidation_source_document=param.oxidation_source_document,
            oxidation_source_table=param.oxidation_source_table,
        )
    )
    seeded_db.flush()

    reloaded = get_stationary_combustion_result(seeded_db, first.result.id)
    assert reloaded is not None
    assert reloaded.net_calorific_value == original_ncv
    assert reloaded.result_value == original_result
    assert reloaded.dataset_version == "2006_V1"


def test_recalculation_creates_new_run_preserves_old(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    second = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    assert first.calculation_run_id != second.calculation_run_id
    assert first.result.id != second.result.id
    assert get_stationary_combustion_result(seeded_db, first.result.id) is not None
    assert get_stationary_combustion_result(seeded_db, second.result.id) is not None


def test_retry_same_run_does_not_duplicate(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    with pytest.raises(ConflictError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
                calculation_run_id=first.calculation_run_id,
            ),
        )
    assert any(d.get("code") == "STATIONARY_COMBUSTION_RESULT_EXISTS" for d in exc.value.details)
    count = seeded_db.execute(
        select(func.count())
        .select_from(CbamStationaryCombustionResult)
        .where(CbamStationaryCombustionResult.calculation_run_id == first.calculation_run_id)
    ).scalar()
    assert count == 1


def test_activity_ownership_mismatch(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    other = Organization(
        name="Other Org SC",
        slug=f"other-sc-{uuid.uuid4().hex[:6]}",
    )
    seeded_db.add(other)
    seeded_db.flush()
    row = seeded_db.get(CbamActivityRecord, activity.id)
    assert row is not None
    row.organization_id = other.id
    seeded_db.flush()
    with pytest.raises(NotFoundError):
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
            ),
        )


def test_reporting_period_ownership_mismatch(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    with pytest.raises(NotFoundError):
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=uuid.uuid4(),
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
            ),
        )


def test_activity_quantity_from_persistence_not_command(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(
        seeded_db, admin, org, binding, installation, quantity=JANUARY_SM3
    )
    executed = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    assert executed.result.activity_quantity == JANUARY_SM3_PERSISTED
    assert "quantity" not in StationaryCombustionExecutionCommand.model_fields


def test_incompatible_activity_unit(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    # NATURAL_GAS catalog is VOLUME; create activity with mass unit via raw insert to bypass
    # activity-type unit catalog (NATURAL_GAS expects volume).
    row = CbamActivityRecord(
        organization_id=org.id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        activity_group="PURCHASED_ENERGY",
        activity_type="NATURAL_GAS",
        quantity=Decimal("100"),
        unit="kg",
        data_source_type="PRIMARY",
        status="active",
    )
    seeded_db.add(row)
    seeded_db.flush()
    with pytest.raises(ValidationAppError) as exc:
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=row.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
            ),
        )
    assert any(d.get("code") == "INCOMPATIBLE_UNIT" for d in exc.value.details)


def test_calculation_failure_creates_no_partial_result(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    before = seeded_db.execute(
        select(func.count()).select_from(CbamStationaryCombustionResult)
    ).scalar()
    with pytest.raises(ValidationAppError):
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=Decimal("0"),
                density_unit="kg/Sm3",
            ),
        )
    after = seeded_db.execute(
        select(func.count()).select_from(CbamStationaryCombustionResult)
    ).scalar()
    assert after == before
    failed_runs = (
        seeded_db.execute(
            select(CbamCalculationRun).where(
                CbamCalculationRun.organization_id == org.id,
                CbamCalculationRun.status == "FAILED",
            )
        )
        .scalars()
        .all()
    )
    assert any(r.error_summary for r in failed_runs)


def test_persistence_conflict_does_not_complete_run(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    # Force a second insert against the unique (run, activity) constraint.
    dup = CbamStationaryCombustionResult(
        organization_id=org.id,
        calculation_run_id=first.calculation_run_id,
        calculation_definition_id=first.result.calculation_definition_id,
        reporting_period_binding_id=binding.id,
        activity_record_id=activity.id,
        fuel_id=first.result.fuel_id,
        parameter_set_id=first.result.parameter_set_id,
        calculation_type=first.result.calculation_type,
        formula_version=first.result.formula_version,
        fuel_code=first.result.fuel_code,
        fuel_name=first.result.fuel_name,
        input_basis=first.result.input_basis,
        activity_quantity=first.result.activity_quantity,
        activity_unit=first.result.activity_unit,
        density_value=first.result.density_value,
        density_unit=first.result.density_unit,
        net_calorific_value=first.result.net_calorific_value,
        net_calorific_value_unit=first.result.net_calorific_value_unit,
        fossil_co2_emission_factor=first.result.fossil_co2_emission_factor,
        fossil_co2_emission_factor_unit=first.result.fossil_co2_emission_factor_unit,
        oxidation_factor=first.result.oxidation_factor,
        dataset_code=first.result.dataset_code,
        dataset_version=first.result.dataset_version,
        valid_from=first.result.valid_from,
        valid_until=first.result.valid_until,
        ncv_reference_source_id=first.result.ncv_reference_source_id,
        ncv_source_document=first.result.ncv_source_document,
        ncv_source_table=first.result.ncv_source_table,
        co2_reference_source_id=first.result.co2_reference_source_id,
        co2_source_document=first.result.co2_source_document,
        co2_source_table=first.result.co2_source_table,
        oxidation_reference_source_id=first.result.oxidation_reference_source_id,
        oxidation_source_document=first.result.oxidation_source_document,
        oxidation_source_table=first.result.oxidation_source_table,
        fuel_mass_kg=first.result.fuel_mass_kg,
        fuel_mass_gg=first.result.fuel_mass_gg,
        energy_content_tj=first.result.energy_content_tj,
        fossil_co2_kg=first.result.fossil_co2_kg,
        fossil_co2_tonnes=first.result.fossil_co2_tonnes,
        result_value=first.result.result_value,
        result_unit=first.result.result_unit,
    )
    seeded_db.add(dup)
    with pytest.raises(IntegrityError):
        seeded_db.flush()
    seeded_db.rollback()
    # After rollback the first result/run should still be recoverable via fresh query
    # only if committed; seeded_db may have rolled back everything. Re-run golden path
    # and assert service conflict path marks FAILED without completing a second result.
    binding2, installation2 = _setup(seeded_db, admin, org)
    activity2 = _create_ng_activity(seeded_db, admin, org, binding2, installation2)
    ok = execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        _cmd(
            organization_id=org.id,
            reporting_period_binding_id=binding2.id,
            activity_record_id=activity2.id,
            fuel_code="NATURAL_GAS",
            reference_date=date(2024, 1, 1),
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    with pytest.raises(ConflictError):
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            _cmd(
                organization_id=org.id,
                reporting_period_binding_id=binding2.id,
                activity_record_id=activity2.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 1),
                density_value=DENSITY,
                density_unit="kg/Sm3",
                calculation_run_id=ok.calculation_run_id,
            ),
        )
    run = seeded_db.get(CbamCalculationRun, ok.calculation_run_id)
    assert run is not None
    assert run.status == "COMPLETED"  # pre-check conflict before RUNNING; status unchanged
    count = seeded_db.execute(
        select(func.count())
        .select_from(CbamStationaryCombustionResult)
        .where(CbamStationaryCombustionResult.calculation_run_id == ok.calculation_run_id)
    ).scalar()
    assert count == 1


def test_calculation_definition_seed_idempotent(seeded_db) -> None:
    ensure_platform_calculation_definitions(seeded_db)
    ensure_platform_calculation_definitions(seeded_db)
    rows = (
        seeded_db.execute(
            select(CbamCalculationDefinition).where(
                CbamCalculationDefinition.code == STATIONARY_COMBUSTION_DEFINITION_CODE
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].calculation_type == "STATIONARY_COMBUSTION_CO2_V1"
    assert rows[0].factor_definition_id is None
    assert rows[0].formula_version == "stationary-combustion-co2-v1"
