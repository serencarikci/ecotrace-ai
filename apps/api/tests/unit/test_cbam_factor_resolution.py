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
    factor_catalog_service,
    factor_resolution_service,
    installation_service,
    period_binding_service,
    purchased_input_service,
    reference_source_service,
)
from ecotrace.modules.cbam.application.activity_record_service import (
    ActivityPropertyInput,
    ActivityRecordCreate,
)
from ecotrace.modules.cbam.application.allocation_rule_service import (
    AllocationRuleCreate,
    AllocationRuleVersionRequest,
)
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
from ecotrace.modules.cbam.infrastructure.models import CbamFactorDefinition, CbamReferenceSource
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
            code=f'P4B-{uuid.uuid4().hex[:8]}',
            name='P4B Installation',
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f'P4B-{uuid.uuid4().hex[:6]}',
        name='P4B Period',
        period_type='custom',
        start_date=date(2031, 1, 1),
        end_date=date(2031, 3, 31),
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


def test_primary_over_default_and_ambiguous(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    definition = _definition(seeded_db, 'NET_CALORIFIC_VALUE')

    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='DIESEL',
            quantity=Decimal('500'),
            unit='L',
            data_source_type='PRIMARY',
            activity_date=date(2031, 2, 1),
            properties=[
                ActivityPropertyInput(
                    property_code='NET_CALORIFIC_VALUE',
                    numeric_value=Decimal('35.8'),
                    unit='MJ/L',
                    source_type='PRIMARY',
                    source_reference='Supplier certificate XYZ',
                )
            ],
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        definition.id,
        activity_type='DIESEL',
        numeric_value=Decimal('36.0'),
        unit='MJ/L',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2035, 12, 31),
    )

    primary = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity.id, 'NET_CALORIFIC_VALUE'
    )
    assert primary.resolution_status == 'RESOLVED_PRIMARY'
    assert primary.selected_value == Decimal('35.8')
    assert primary.selected_unit == 'MJ/L'
    assert primary.selected_activity_property_id is not None

    activity2 = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='DIESEL',
            quantity=Decimal('500'),
            unit='L',
            data_source_type='PRIMARY',
            activity_date=date(2031, 2, 1),
        ),
    )
    defaulted = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity2.id, 'NET_CALORIFIC_VALUE'
    )
    assert defaulted.resolution_status == 'RESOLVED_DEFAULT'
    assert defaulted.selected_value == Decimal('36.0')

    _activate_value(
        seeded_db,
        admin,
        org.id,
        definition.id,
        activity_type='DIESEL',
        numeric_value=Decimal('36.2'),
        unit='MJ/L',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2030, 1, 1),
        valid_until=date(2035, 12, 31),
        source_reference='second default',
    )
    ambiguous = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity2.id, 'NET_CALORIFIC_VALUE', reresolve=True
    )
    assert ambiguous.resolution_status == 'AMBIGUOUS'
    assert ambiguous.selected_value is None


def test_validity_and_unresolved(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    definition = _definition(seeded_db, 'NET_CALORIFIC_VALUE')
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='DIESEL',
            quantity=Decimal('10'),
            unit='L',
            data_source_type='PRIMARY',
            activity_date=date(2031, 6, 1),
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        definition.id,
        activity_type='DIESEL',
        numeric_value=Decimal('36.0'),
        unit='MJ/L',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2020, 1, 1),
        valid_until=date(2025, 12, 31),
    )
    expired = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, activity.id, 'NET_CALORIFIC_VALUE'
    )
    assert expired.resolution_status in {'OUTSIDE_VALIDITY', 'UNRESOLVED'}

    future_only = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='GASOLINE',
            quantity=Decimal('10'),
            unit='L',
            data_source_type='PRIMARY',
            activity_date=date(2031, 6, 1),
        ),
    )
    _activate_value(
        seeded_db,
        admin,
        org.id,
        definition.id,
        activity_type='GASOLINE',
        numeric_value=Decimal('37.0'),
        unit='MJ/L',
        data_source_type='DEFAULT_REFERENCE',
        valid_from=date(2032, 1, 1),
        valid_until=date(2039, 12, 31),
        source_reference='future',
    )
    future = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, future_only.id, 'NET_CALORIFIC_VALUE'
    )
    assert future.resolution_status in {'OUTSIDE_VALIDITY', 'UNRESOLVED'}

    bare = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='NATURAL_GAS',
            quantity=Decimal('1'),
            unit='m3',
            data_source_type='PRIMARY',
        ),
    )
    unresolved = factor_resolution_service.resolve_for_activity_record(
        seeded_db, admin, org.id, bare.id, 'NET_CALORIFIC_VALUE'
    )
    assert unresolved.resolution_status == 'UNRESOLVED'


def test_purchased_embedded_primary_and_no_fabrication(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    with_primary = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name='Precursor',
            quantity=Decimal('10'),
            unit='t',
            embedded_emission_value=Decimal('1.25'),
            embedded_emission_unit='tCO2e/t',
            embedded_emission_source_type='PRIMARY',
            source_reference='supplier EE',
        ),
    )
    resolved = factor_resolution_service.resolve_for_purchased_input(
        seeded_db, admin, org.id, with_primary.id, 'SUPPLIER_EMBEDDED_EMISSION'
    )
    assert resolved.resolution_status == 'RESOLVED_PRIMARY'
    assert resolved.selected_value == Decimal('1.25')
    assert resolved.selected_unit == 'tCO2e/t'

    without = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name='No EE',
            quantity=Decimal('5'),
            unit='t',
            embedded_emission_source_type='NOT_PROVIDED',
        ),
    )
    missing = factor_resolution_service.resolve_for_purchased_input(
        seeded_db, admin, org.id, without.id, 'SUPPLIER_EMBEDDED_EMISSION'
    )
    assert missing.resolution_status == 'UNRESOLVED'
    assert missing.selected_value is None


def test_allocation_result_resolution_no_multiply(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='DIESEL',
            quantity=Decimal('100'),
            unit='L',
            data_source_type='PRIMARY',
            properties=[
                ActivityPropertyInput(
                    property_code='NET_CALORIFIC_VALUE',
                    numeric_value=Decimal('35.8'),
                    unit='MJ/L',
                    source_type='PRIMARY',
                )
            ],
        ),
    )
    rule = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            installation_profile_id=installation.id,
            allocation_method='DIRECT_ASSIGNMENT',
            name='Direct',
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
    assert alloc.allocated_quantity == Decimal('100')
    resolved = factor_resolution_service.resolve_for_allocation_result(
        seeded_db, admin, org.id, alloc.id, 'NET_CALORIFIC_VALUE'
    )
    assert resolved.resolution_status == 'RESOLVED_PRIMARY'
    assert resolved.selected_value == Decimal('35.8')
    refreshed = allocation_service.get_allocation_result(seeded_db, admin, org.id, alloc.id)
    assert refreshed.allocated_quantity == Decimal('100')
    assert not hasattr(refreshed, 'calculated_emission')

    again = factor_resolution_service.resolve_for_allocation_result(
        seeded_db, admin, org.id, alloc.id, 'NET_CALORIFIC_VALUE', reresolve=True
    )
    assert again.id != resolved.id
    assert again.is_current is True


def test_reference_sources_metadata_only(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    page = reference_source_service.list_reference_sources(
        seeded_db, admin, org.id, page=1, page_size=50
    )
    codes = {item.code for item in page.items}
    assert {'IPCC', 'DEFRA', 'EPA'}.issubset(codes)
    defs = factor_catalog_service.list_factor_definitions(
        seeded_db, admin, org.id, page=1, page_size=50
    )
    assert any(d.code == 'NET_CALORIFIC_VALUE' for d in defs.items)
    ncv = _definition(seeded_db, 'NET_CALORIFIC_VALUE')
    values = factor_catalog_service.list_factor_values(
        seeded_db, admin, org.id, ncv.id, page=1, page_size=50
    )
    assert values.total_items == 0


def test_phase4b_no_emission_multiplication_in_sources() -> None:
    assert find_forbidden_imports_in_tree() == []
    api_root = Path(__file__).resolve().parents[2]
    files = [
        api_root / 'src/ecotrace/modules/cbam/application/factor_resolution_service.py',
        api_root / 'src/ecotrace/modules/cbam/application/factor_catalog_service.py',
        api_root / 'src/ecotrace/modules/cbam/application/reference_source_service.py',
        api_root / 'src/ecotrace/modules/cbam/application/factor_catalog_seed.py',
    ]
    banned = (
        'activity_quantity *',
        'allocated_quantity *',
        'emission_factor *',
        'calculate_co2',
        'co2e_total',
        'openpyxl',
        'xlsxwriter',
        'requests.get',
        'httpx.get',
        'urllib.request',
    )
    for path in files:
        text = path.read_text(encoding='utf-8')
        lower = text.lower()
        for token in banned:
            assert token not in lower, f'{path} contains {token}'
        assert 'calculated_emission' not in lower
        assert 'total_emission' not in lower
