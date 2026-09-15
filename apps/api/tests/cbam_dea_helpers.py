"""Shared fixtures for Phase 7A-2 direct-emissions allocation tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    installation_service,
    monthly_production_basis_service,
    period_binding_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
)
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    StationaryCombustionExecutionCommand,
    execute_stationary_combustion_calculation,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

DENSITY = Decimal("0.68")

# Workbook natural-gas months (quantity Sm3, D tonnes, E tonnes)
WORKBOOK_MONTHS = [
    (date(2024, 7, 15), Decimal("188"), Decimal("506"), Decimal("39.34")),
    (date(2024, 8, 15), Decimal("183"), Decimal("421"), Decimal("29.69")),
    (date(2024, 9, 15), Decimal("490"), Decimal("337"), Decimal("34.56")),
]

# Exact Stage-1 / Stage-2 golden values for WORKBOOK_MONTHS @ density 0.68
# (Defined with high Decimal precision — do not subtract under default prec=28.)
GOLDEN_FACILITY_FOSSIL_CO2_RAW = Decimal("1.576580544")
GOLDEN_CBAM_FOSSIL_CO2_RAW = Decimal("0.14240956741791274806009246833831264129277932416046")
GOLDEN_NON_CBAM_FOSSIL_CO2_RAW = Decimal("1.4341709765820872519399075316616873587072206758395")
# PostgreSQL Numeric(36, 18) round-trip of the raw CBAM pool
GOLDEN_CBAM_FOSSIL_CO2_RAW_STORED = Decimal("0.142409567417912748")
GOLDEN_FACILITY_FOSSIL_CO2_RAW_STORED = Decimal("1.576580544000000000")
GOLDEN_NON_CBAM_FOSSIL_CO2_RAW_STORED = Decimal("1.434170976582087252")
GOLDEN_CBAM_POOL_FINAL = Decimal("0.14240957")
GOLDEN_FACILITY_FINAL = Decimal("1.57658054")
GOLDEN_NON_CBAM_FINAL = Decimal("1.43417097")
GOLDEN_REMAINING = Decimal("0")
GOLDEN_PRODUCT_FINALS_BY_QTY = {
    Decimal("39.34"): Decimal("0.05408237"),
    Decimal("29.69"): Decimal("0.04081610"),
    Decimal("34.56"): Decimal("0.04751110"),
}


def org(db: Session) -> Organization:
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def admin(db: Session) -> User:
    return db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()


def setup_binding(
    db: Session,
    user: User,
    organization: Organization,
    *,
    start: date = date(2024, 7, 1),
    end: date = date(2024, 9, 30),
):
    facility = db.execute(
        select(Facility).where(Facility.organization_id == organization.id).limit(1)
    ).scalar_one()
    installation_service.create_installation(
        db,
        user,
        organization.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"DEA-{uuid.uuid4().hex[:8]}",
            name="DEA Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=organization.id,
        code=f"DEA-{uuid.uuid4().hex[:6]}",
        name="DEA Period",
        period_type="custom",
        start_date=start,
        end_date=end,
        status="open",
    )
    db.add(period)
    db.flush()
    binding = period_binding_service.create_period_binding(
        db, user, organization.id, PeriodBindingCreate(reporting_period_id=period.id)
    )
    opened = period_binding_service.open_data_collection(
        db,
        user,
        organization.id,
        binding.id,
        PeriodBindingVersionRequest(row_version=binding.row_version),
    )
    installation = installation_service.list_installations(
        db, user, organization.id, page=1, page_size=50
    ).items[-1]
    return opened, installation


def create_ng_activity(
    db, user, organization, binding, installation, *, qty, day, fuel="NATURAL_GAS"
):
    return activity_record_service.create_activity_record(
        db,
        user,
        organization.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type=fuel,
            quantity=qty,
            unit="Sm3",
            data_source_type="PRIMARY",
            activity_date=day,
        ),
    )


def run_sc(db, user, organization, binding, activity, *, day, fuel="NATURAL_GAS", density=DENSITY):
    return execute_stationary_combustion_calculation(
        db,
        user,
        StationaryCombustionExecutionCommand(
            organization_id=organization.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code=fuel,
            reference_date=day,
            density_value=density,
            density_unit="kg/Sm3",
            requested_by_user_id=user.id,
            client_request_id=uuid.uuid4(),
        ),
    )


def seed_workbook_ready_allocation(db: Session, user: User, organization: Organization):
    """Three workbook months with matching D/E, SC, and production EXACT_MATCH."""
    binding, installation = setup_binding(db, user, organization)
    for day, qty, d, e in WORKBOOK_MONTHS:
        act = create_ng_activity(db, user, organization, binding, installation, qty=qty, day=day)
        run_sc(db, user, organization, binding, act, day=day)
        monthly_production_basis_service.create_monthly_production_basis(
            db,
            user,
            organization.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(day.year, day.month, 1),
                total_production_quantity=d,
                cbam_quantity=e,
                quantity_unit="t",
            ),
        )
        product = ensure_org_product(
            db, organization.id, code=f"P-{day.month}-{uuid.uuid4().hex[:4]}"
        )
        profile = create_active_ready_profile(db, user, organization.id, product=product)
        production_record_service.create_production_record(
            db,
            user,
            organization.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=profile.id,
                quantity=e,
                unit="t",
                production_date=day,
            ),
        )
    return binding, installation
