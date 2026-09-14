"""Phase 7A-0 monthly production-basis (workbook D/E) tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from tests.cbam_profile_helpers import create_active_ready_profile

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    installation_service,
    monthly_production_basis_service,
    period_binding_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
    MonthlyProductionBasisUpdate,
    iter_expected_months,
)
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
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


def _setup_quarter(db, admin, org, *, start=date(2030, 1, 1), end=date(2030, 3, 31)):
    facility = db.execute(
        select(Facility).where(Facility.organization_id == org.id).limit(1)
    ).scalar_one()
    installation_service.create_installation(
        db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f'MPB-{uuid.uuid4().hex[:8]}',
            name='MPB Installation',
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f'MPB-{uuid.uuid4().hex[:6]}',
        name='MPB Period',
        period_type='custom',
        start_date=start,
        end_date=end,
        status='open',
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
    return opened, installation, period


def test_quarterly_binding_expected_three_months() -> None:
    months = iter_expected_months(date(2030, 1, 15), date(2030, 3, 10))
    assert months == [date(2030, 1, 1), date(2030, 2, 1), date(2030, 3, 1)]


def test_create_valid_month_and_share(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _period = _setup_quarter(seeded_db, admin, org)
    created = monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 1, 1),
            total_production_quantity=Decimal('506'),
            cbam_quantity=Decimal('39.34'),
            quantity_unit='t',
        ),
    )
    assert created.status == 'READY'
    assert created.cbam_share == (Decimal('39.34') / Decimal('506')).quantize(
        Decimal('0.000000000001')
    )
    assert created.normalized_total_production_tonnes == Decimal('506')
    assert created.issue_codes == []


def test_duplicate_month_rejected(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _ = _setup_quarter(seeded_db, admin, org)
    payload = MonthlyProductionBasisCreate(
        month_start=date(2030, 2, 1),
        total_production_quantity=Decimal('100'),
        cbam_quantity=Decimal('10'),
    )
    monthly_production_basis_service.create_monthly_production_basis(
        seeded_db, admin, org.id, binding.id, payload
    )
    with pytest.raises(ConflictError) as exc:
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db, admin, org.id, binding.id, payload
        )
    assert exc.value.details[0]['code'] == 'MONTHLY_PRODUCTION_BASIS_DUPLICATE'


def test_cross_org_and_outside_month(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _ = _setup_quarter(seeded_db, admin, org)
    with pytest.raises((NotFoundError, BusinessRuleError)):
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            uuid.uuid4(),
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(2030, 1, 1),
                total_production_quantity=Decimal('1'),
                cbam_quantity=Decimal('1'),
            ),
        )
    with pytest.raises(BusinessRuleError) as exc:
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            org.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(2030, 4, 1),
                total_production_quantity=Decimal('1'),
                cbam_quantity=Decimal('1'),
            ),
        )
    assert exc.value.details[0]['code'] == 'MONTH_OUTSIDE_REPORTING_PERIOD'


def test_decimal_unit_and_rules(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _ = _setup_quarter(seeded_db, admin, org)
    kg_row = monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 1, 1),
            total_production_quantity=Decimal('506000'),
            cbam_quantity=Decimal('39340'),
            quantity_unit='kg',
        ),
    )
    assert kg_row.normalized_total_production_tonnes == Decimal('506')
    assert kg_row.normalized_cbam_quantity_tonnes == Decimal('39.34')

    with pytest.raises(ValidationAppError) as vol:
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            org.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(2030, 2, 1),
                total_production_quantity=Decimal('1'),
                cbam_quantity=Decimal('1'),
                quantity_unit='Sm3',
            ),
        )
    assert vol.value.details[0]['code'] == 'INCOMPATIBLE_PRODUCTION_UNIT'

    with pytest.raises(BusinessRuleError) as gt:
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            org.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(2030, 2, 1),
                total_production_quantity=Decimal('10'),
                cbam_quantity=Decimal('11'),
            ),
        )
    assert gt.value.details[0]['code'] == 'CBAM_QUANTITY_EXCEEDS_TOTAL'

    with pytest.raises(BusinessRuleError) as zero_d:
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            org.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(2030, 2, 1),
                total_production_quantity=Decimal('0'),
                cbam_quantity=Decimal('1'),
            ),
        )
    assert zero_d.value.details[0]['code'] == 'TOTAL_PRODUCTION_MUST_BE_POSITIVE'

    zero_e = monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 2, 1),
            total_production_quantity=Decimal('100'),
            cbam_quantity=Decimal('0'),
        ),
    )
    assert zero_e.status == 'READY'
    assert zero_e.cbam_share == Decimal('0').quantize(Decimal('0.000000000001'))


def test_incomplete_draft_and_summary_missing(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _ = _setup_quarter(seeded_db, admin, org)
    incomplete = monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 1, 1),
            total_production_quantity=Decimal('100'),
            cbam_quantity=None,
        ),
    )
    assert incomplete.status == 'INCOMPLETE'
    assert 'CBAM_QUANTITY_REQUIRED' in incomplete.issue_codes

    summary = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    assert summary.expected_month_count == 3
    assert summary.incomplete_month_count == 1
    assert summary.missing_month_count == 2
    assert summary.allocation_basis_ready is False
    assert 'MONTHLY_PRODUCTION_BASIS_MISSING' in summary.blocking_issue_codes
    assert 'sum(E)/sum(D)' not in str(summary.model_dump())
    assert not hasattr(summary, 'period_wide_cbam_share')


def test_summary_never_exposes_period_ratio_field(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _ = _setup_quarter(seeded_db, admin, org)
    for month, d, e in (
        (date(2030, 1, 1), '506', '39.34'),
        (date(2030, 2, 1), '421', '29.69'),
        (date(2030, 3, 1), '337', '34.56'),
    ):
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            org.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=month,
                total_production_quantity=Decimal(d),
                cbam_quantity=Decimal(e),
            ),
        )
    summary = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    dumped = summary.model_dump()
    assert 'allocationShare' not in dumped
    assert 'periodWideShare' not in dumped
    assert summary.completed_month_count == 3
    assert summary.allocation_basis_ready is True


def test_production_reconciliation_exact_and_mismatch(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _ = _setup_quarter(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 1, 1),
            total_production_quantity=Decimal('100'),
            cbam_quantity=Decimal('40'),
        ),
    )
    production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            production_date=date(2030, 1, 15),
            quantity=Decimal('40'),
            unit='t',
        ),
    )
    summary = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    jan = next(r for r in summary.production_reconciliation if r.month_start == date(2030, 1, 1))
    assert jan.reconciliation_status == 'EXACT_MATCH'
    assert jan.difference_tonnes == Decimal('0')

    # Patch E without touching production → mismatch; E not overwritten.
    row = monthly_production_basis_service.list_monthly_production_basis(
        seeded_db, admin, org.id, binding.id, page=1, page_size=10
    ).items[0]
    updated = monthly_production_basis_service.update_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        row.id,
        MonthlyProductionBasisUpdate(row_version=row.row_version, cbam_quantity=Decimal('41')),
    )
    assert updated.cbam_quantity == Decimal('41')
    summary2 = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    jan2 = next(r for r in summary2.production_reconciliation if r.month_start == date(2030, 1, 1))
    assert jan2.reconciliation_status == 'MISMATCH'
    assert jan2.difference_tonnes == Decimal('1')
    assert jan2.explicit_cbam_quantity_tonnes == Decimal('41')


def test_undated_production_reconciliation_unavailable(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _ = _setup_quarter(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 1, 1),
            total_production_quantity=Decimal('100'),
            cbam_quantity=Decimal('10'),
        ),
    )
    production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            production_date=None,
            quantity=Decimal('10'),
            unit='t',
        ),
    )
    summary = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    assert all(r.reconciliation_status == 'UNAVAILABLE' for r in summary.production_reconciliation)


def test_combustion_date_compatibility(seeded_db) -> None:
    from ecotrace.modules.cbam.application import activity_record_service
    from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
    from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
        StationaryCombustionExecutionCommand,
        execute_stationary_combustion_calculation,
    )

    org = _org(seeded_db)
    admin = _admin(seeded_db)
    # Use Jan–Mar 2024 to match typical SC seed density/reference dates.
    binding, installation, _ = _setup_quarter(
        seeded_db, admin, org, start=date(2024, 1, 1), end=date(2024, 3, 31)
    )
    undated = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='NATURAL_GAS',
            quantity=Decimal('100'),
            unit='Sm3',
            data_source_type='PRIMARY',
            activity_date=None,
        ),
    )
    execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        StationaryCombustionExecutionCommand(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=undated.id,
            fuel_code='NATURAL_GAS',
            reference_date=date(2024, 1, 15),
            density_value=Decimal('0.67'),
            density_unit='kg/Sm3',
            requested_by_user_id=admin.id,
            client_request_id=uuid.uuid4(),
            request_fingerprint='mpb-undated',
        ),
        commit=True,
    )
    summary = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    assert summary.combustion_compatibility_status == 'BLOCKED'
    assert 'COMBUSTION_ACTIVITY_DATE_REQUIRED' in summary.combustion_compatibility_issue_codes

    dated = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type='NATURAL_GAS',
            quantity=Decimal('100'),
            unit='Sm3',
            data_source_type='PRIMARY',
            activity_date=date(2024, 2, 10),
        ),
    )
    execute_stationary_combustion_calculation(
        seeded_db,
        admin,
        StationaryCombustionExecutionCommand(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=dated.id,
            fuel_code='NATURAL_GAS',
            reference_date=date(2024, 2, 10),
            density_value=Decimal('0.67'),
            density_unit='kg/Sm3',
            requested_by_user_id=admin.id,
            client_request_id=uuid.uuid4(),
            request_fingerprint='mpb-dated',
        ),
        commit=True,
    )
    # Fill READY basis for February only — dated source maps to Feb.
    monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2024, 2, 1),
            total_production_quantity=Decimal('100'),
            cbam_quantity=Decimal('10'),
        ),
    )
    summary2 = monthly_production_basis_service.get_monthly_production_basis_summary(
        seeded_db, admin, org.id, binding.id
    )
    dated_item = next(
        i for i in summary2.combustion_items if i.activity_record_id == dated.id
    )
    assert dated_item.month_start == date(2024, 2, 1)
    assert dated_item.status == 'READY'
    undated_item = next(
        i for i in summary2.combustion_items if i.activity_record_id == undated.id
    )
    assert undated_item.status == 'BLOCKED'
    assert 'COMBUSTION_ACTIVITY_DATE_REQUIRED' in undated_item.issue_codes



def test_delete_and_non_canonical_month(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, _inst, _ = _setup_quarter(seeded_db, admin, org)
    with pytest.raises(ValidationAppError):
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            admin,
            org.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(2030, 1, 15),
                total_production_quantity=Decimal('1'),
                cbam_quantity=Decimal('1'),
            ),
        )
    created = monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        admin,
        org.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2030, 1, 1),
            total_production_quantity=Decimal('1'),
            cbam_quantity=Decimal('1'),
        ),
    )
    monthly_production_basis_service.delete_monthly_production_basis(
        seeded_db, admin, org.id, created.id
    )
    with pytest.raises(NotFoundError):
        monthly_production_basis_service.get_monthly_production_basis(
            seeded_db, admin, org.id, created.id
        )


def test_monthly_prod_basis_migration_round_trip(seeded_db) -> None:
    seeded_db.execute(text('DROP TABLE IF EXISTS cbam_monthly_production_basis CASCADE'))
    seeded_db.flush()

    def upgrade() -> None:
        seeded_db.execute(
            text(
                """
CREATE TABLE cbam_monthly_production_basis (
    id UUID NOT NULL,
    organization_id UUID NOT NULL,
    reporting_period_binding_id UUID NOT NULL,
    month_start DATE NOT NULL,
    total_production_quantity NUMERIC(24, 8),
    cbam_quantity NUMERIC(24, 8),
    quantity_unit VARCHAR(32) NOT NULL,
    source_type VARCHAR(32) NOT NULL DEFAULT 'MANUAL',
    notes TEXT,
    row_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    CONSTRAINT pk_cbam_monthly_production_basis PRIMARY KEY (id),
    CONSTRAINT uq_cbam_monthly_prod_basis_org_binding_month
        UNIQUE (organization_id, reporting_period_binding_id, month_start),
    CONSTRAINT ck_cbam_monthly_prod_basis_month_canonical
        CHECK (EXTRACT(DAY FROM month_start) = 1)
)
"""
            )
        )
        seeded_db.flush()

    def downgrade() -> None:
        seeded_db.execute(text('DROP TABLE IF EXISTS cbam_monthly_production_basis CASCADE'))
        seeded_db.flush()

    upgrade()
    assert seeded_db.execute(
        text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name='cbam_monthly_production_basis'"
        )
    ).scalar()
    downgrade()
    assert (
        seeded_db.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name='cbam_monthly_production_basis'"
            )
        ).scalar()
        is None
    )
    upgrade()
