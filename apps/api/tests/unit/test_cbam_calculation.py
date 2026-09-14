from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    allocation_rule_service,
    allocation_service,
    calculation_service,
    factor_catalog_service,
    factor_resolution_service,
    installation_service,
    period_binding_service,
    purchased_input_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.allocation_rule_service import (
    AllocationRuleCreate,
    AllocationRuleVersionRequest,
)
from ecotrace.modules.cbam.application.calculation_math import multiply_activity_by_factor
from ecotrace.modules.cbam.application.calculation_service import CalculationRunExecuteRequest
from ecotrace.modules.cbam.application.factor_catalog_service import (
    FactorValueCreate,
    FactorValueVersionRequest,
)
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_input_service import PurchasedInputCreate
from ecotrace.modules.cbam.architecture_boundary import find_forbidden_imports_in_tree
from ecotrace.modules.cbam.infrastructure.models import (
    CbamCalculationDefinition,
    CbamCalculationResult,
    CbamFactorDefinition,
    CbamReferenceSource,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


def _org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db):
    return db.execute(
        select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
    ).scalar_one()


def _facility(db, org_id):
    return db.execute(select(Facility).where(Facility.organization_id == org_id).limit(1)).scalar_one()


def _setup(db, admin, org):
    facility = _facility(db, org.id)
    installation_service.create_installation(
        db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f'P5-{uuid.uuid4().hex[:8]}',
            name='P5 Installation',
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f'P5-{uuid.uuid4().hex[:6]}',
        name='P5 Period',
        period_type='custom',
        start_date=date(2032, 1, 1),
        end_date=date(2032, 3, 31),
        status='open',
    )
    db.add(period)
    db.commit()
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


def _definition(db, code: str) -> CbamFactorDefinition:
    return db.execute(
        select(CbamFactorDefinition).where(CbamFactorDefinition.code == code)
    ).scalar_one()


def _manual_source(db) -> CbamReferenceSource:
    return db.execute(
        select(CbamReferenceSource).where(
            CbamReferenceSource.organization_id.is_(None),
            CbamReferenceSource.code == 'MANUAL_APPROVED_REFERENCE',
        )
    ).scalar_one()


def _activate_value(db, admin, org_id, definition_id, **kwargs):
    created = factor_catalog_service.create_factor_value(
        db,
        admin,
        org_id,
        definition_id,
        FactorValueCreate(
            reference_source_id=_manual_source(db).id,
            **kwargs,
        ),
    )
    return factor_catalog_service.activate_factor_value(
        db,
        admin,
        org_id,
        created.id,
        FactorValueVersionRequest(row_version=created.row_version),
    )


def test_multiply_math_examples() -> None:
    a = multiply_activity_by_factor(
        activity_quantity=Decimal('100'),
        activity_unit='kWh',
        factor_value=Decimal('0.5'),
        factor_unit='kgCO2e/kWh',
    )
    assert a.ok
    assert a.result_value == Decimal('50.00000000')
    assert a.result_unit == 'kgCO2e'

    b = multiply_activity_by_factor(
        activity_quantity=Decimal('20'),
        activity_unit='MWh',
        factor_value=Decimal('0.4'),
        factor_unit='tCO2e/MWh',
    )
    assert b.ok
    assert b.result_value == Decimal('8.00000000')
    assert b.result_unit == 'tCO2e'

    bad = multiply_activity_by_factor(
        activity_quantity=Decimal('100'),
        activity_unit='L',
        factor_value=Decimal('0.5'),
        factor_unit='kgCO2e/kWh',
    )
    assert not bad.ok
    assert bad.error_code == 'INCOMPATIBLE_UNIT'


def test_activity_calculation_and_blocks(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ef = _definition(seeded_db, 'GENERIC_EMISSION_FACTOR')

    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='ELECTRICITY',
            quantity=Decimal('100'),
            unit='kWh',
            data_source_type='PRIMARY',
            activity_date=date(2032, 2, 1),
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        ef.id,
        activity_type='ELECTRICITY',
        numeric_value=Decimal('0.5'),
        unit='kgCO2e/kWh',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2040, 12, 31),
    )
    resolved = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity.id, 'GENERIC_EMISSION_FACTOR'
    )
    assert resolved.resolution_status == 'RESOLVED_DEFAULT'

    run = calculation_service.create_calculation_run(seeded_db, admin, org.id, binding.id)
    executed = calculation_service.execute_calculation_run(
        seeded_db,
        admin,
        org.id,
        run.id,
        CalculationRunExecuteRequest(allow_unallocated_activity=True),
    )
    assert executed.status in {'COMPLETED', 'PARTIALLY_COMPLETED'}
    assert executed.calculated_count >= 1

    results = calculation_service.list_calculation_results(
        seeded_db, admin, org.id, executed.id, page=1, page_size=50
    ).items
    calc = next(r for r in results if r.source_id == activity.id and r.status == 'CALCULATED')
    assert calc.result_value == Decimal('50.00000000')
    assert calc.result_unit == 'kgCO2e'
    assert calc.source_quantity == Decimal('100.00000000')
    assert calc.factor_value == Decimal('0.50000000')


def test_ambiguous_and_unresolved_block(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ef = _definition(seeded_db, 'GENERIC_EMISSION_FACTOR')

    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='ELECTRICITY',
            quantity=Decimal('10'),
            unit='kWh',
            data_source_type='PRIMARY',
            activity_date=date(2032, 2, 1),
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        ef.id,
        activity_type='ELECTRICITY',
        numeric_value=Decimal('0.4'),
        unit='kgCO2e/kWh',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2040, 12, 31),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        ef.id,
        activity_type='ELECTRICITY',
        numeric_value=Decimal('0.5'),
        unit='kgCO2e/kWh',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2040, 12, 31),
    )
    ambiguous = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity.id, 'GENERIC_EMISSION_FACTOR'
    )
    assert ambiguous.resolution_status == 'AMBIGUOUS'

    run = calculation_service.create_calculation_run(seeded_db, admin, org.id, binding.id)
    executed = calculation_service.execute_calculation_run(seeded_db, admin, org.id, run.id)
    results = calculation_service.list_calculation_results(
        seeded_db, admin, org.id, executed.id, page=1, page_size=50
    ).items
    blocked = [r for r in results if r.source_id == activity.id]
    assert blocked
    assert all(r.result_value is None for r in blocked)
    assert any(r.status == 'AMBIGUOUS_FACTOR' for r in blocked)


def test_allocation_quantity_preferred(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ef = _definition(seeded_db, 'GENERIC_EMISSION_FACTOR')

    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='ELECTRICITY',
            quantity=Decimal('100'),
            unit='MWh',
            data_source_type='PRIMARY',
            activity_date=date(2032, 2, 1),
        ),
    )
    rule = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            name='Direct power',
            installation_profile_id=installation.id,
            allocation_method='DIRECT_ASSIGNMENT',
        ),
    )
    active = allocation_rule_service.activate_allocation_rule(
        seeded_db,
        admin,
        org.id,
        rule.id,
        AllocationRuleVersionRequest(row_version=rule.row_version),
    )
    alloc = allocation_service.allocate_activity_record(
        seeded_db, admin, org.id, active.id, activity.id
    )
    assert alloc.allocated_quantity == Decimal('100.00000000')

    _activate_value(
        seeded_db,
        admin,
        org.id,
        ef.id,
        activity_type='ELECTRICITY',
        numeric_value=Decimal('0.4'),
        unit='tCO2e/MWh',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2040, 12, 31),
    )
    factor_resolution_service.resolve_for_allocation_result(
        seeded_db, admin, org.id, alloc.id, 'GENERIC_EMISSION_FACTOR'
    )

    calc_def = seeded_db.execute(
        select(CbamCalculationDefinition).where(
            CbamCalculationDefinition.code == 'MULTIPLY_ALLOCATION_BY_GENERIC_EF'
        )
    ).scalar_one()
    run = calculation_service.create_calculation_run(seeded_db, admin, org.id, binding.id)
    executed = calculation_service.execute_calculation_run(
        seeded_db,
        admin,
        org.id,
        run.id,
        CalculationRunExecuteRequest(calculation_definition_ids=[calc_def.id]),
    )
    results = calculation_service.list_calculation_results(
        seeded_db, admin, org.id, executed.id, page=1, page_size=50
    ).items
    row = next(r for r in results if r.source_type == 'ALLOCATION_RESULT')
    assert row.status == 'CALCULATED'
    assert row.result_value == Decimal('40.00000000')
    assert row.result_unit == 'tCO2e'
    assert row.source_quantity == Decimal('100.00000000')


def test_purchased_uses_consumed_not_purchased(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ef = _definition(seeded_db, 'GENERIC_EMISSION_FACTOR')

    purchased = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name='Steel precursor',
            quantity=Decimal('500'),
            unit='t',
            received_date=date(2032, 2, 1),
            consumed_quantity=Decimal('20'),
            consumed_unit='t',
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        ef.id,
        activity_type=None,
        numeric_value=Decimal('0.4'),
        unit='tCO2e/t',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2040, 12, 31),
    )
    factor_resolution_service.resolve_for_purchased_input(
        seeded_db, admin, org.id, purchased.id, 'GENERIC_EMISSION_FACTOR'
    )
    calc_def = seeded_db.execute(
        select(CbamCalculationDefinition).where(
            CbamCalculationDefinition.code == 'MULTIPLY_PURCHASED_BY_GENERIC_EF'
        )
    ).scalar_one()
    run = calculation_service.create_calculation_run(seeded_db, admin, org.id, binding.id)
    executed = calculation_service.execute_calculation_run(
        seeded_db,
        admin,
        org.id,
        run.id,
        CalculationRunExecuteRequest(calculation_definition_ids=[calc_def.id]),
    )
    results = calculation_service.list_calculation_results(
        seeded_db, admin, org.id, executed.id, page=1, page_size=50
    ).items
    row = next(
        r
        for r in results
        if r.source_id == purchased.id
        and r.calculation_definition_id == calc_def.id
    )
    assert row.status == 'CALCULATED', row.error_message
    assert row.source_quantity == Decimal('20.00000000')
    assert row.result_value == Decimal('8.00000000')
    assert row.result_unit == 'tCO2e'


def test_recalculate_preserves_history(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    ef = _definition(seeded_db, 'GENERIC_EMISSION_FACTOR')
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='ELECTRICITY',
            quantity=Decimal('100'),
            unit='kWh',
            data_source_type='PRIMARY',
            activity_date=date(2032, 2, 1),
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        ef.id,
        activity_type='ELECTRICITY',
        numeric_value=Decimal('0.5'),
        unit='kgCO2e/kWh',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2040, 12, 31),
    )
    factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity.id, 'GENERIC_EMISSION_FACTOR'
    )
    run = calculation_service.create_calculation_run(seeded_db, admin, org.id, binding.id)
    executed = calculation_service.execute_calculation_run(seeded_db, admin, org.id, run.id)
    first = next(
        r
        for r in calculation_service.list_calculation_results(
            seeded_db, admin, org.id, executed.id, page=1, page_size=50
        ).items
        if r.source_id == activity.id and r.status == 'CALCULATED'
    )
    again = calculation_service.recalculate_result(seeded_db, admin, org.id, first.id)
    assert again.id != first.id
    assert again.is_current is True
    old = seeded_db.execute(
        select(CbamCalculationResult).where(CbamCalculationResult.id == first.id)
    ).scalar_one()
    assert old.is_current is False
    assert old.superseded_at is not None


def test_phase5_no_guessing_and_architecture() -> None:
    assert find_forbidden_imports_in_tree() == []
    api_root = Path(__file__).resolve().parents[2]
    paths = [
        api_root / 'src/ecotrace/modules/cbam/application/calculation_math.py',
        api_root / 'src/ecotrace/modules/cbam/application/stationary_combustion_math.py',
        api_root / 'src/ecotrace/modules/cbam/application/calculation_service.py',
        api_root / 'src/ecotrace/db/migrations/versions/0012_cbam_minimal_calculation.py',
    ]
    banned = (
        'fetch_ipcc',
        'fetch_defra',
        'gwp_table',
        'density_assumption',
        'openpyxl',
        'xlsxwriter',
        'co2_to_co2e',
    )
    for path in paths:
        text = path.read_text(encoding='utf-8').lower()
        for token in banned:
            assert token not in text, f'{path} contains banned token {token}'
    migration = paths[2].read_text(encoding='utf-8')
    assert 'INSERT INTO cbam_factor_values' not in migration
    assert '0.4' not in migration
    assert '0.5' not in migration
