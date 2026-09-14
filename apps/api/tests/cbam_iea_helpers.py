"""Shared fixtures / goldens for Phase 8C indirect-emissions allocation tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application import (
    activity_record_service,
    monthly_production_basis_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    PurchasedElectricityExecuteRequest,
    PurchasedElectricityManualFactor,
    execute_purchased_electricity,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from tests.cbam_dea_helpers import admin, org, setup_binding
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

# Workbook electricity months: (activity_date, kWh, D tonnes, E tonnes)
WORKBOOK_ELEC_MONTHS = [
    (date(2024, 7, 15), Decimal("176034.53"), Decimal("506"), Decimal("39.34")),
    (date(2024, 8, 15), Decimal("180962.85"), Decimal("421"), Decimal("29.69")),
    (date(2024, 9, 15), Decimal("144768.90"), Decimal("337"), Decimal("34.56")),
]

H4 = Decimal("0.439")

# Stage 1 goldens (monthly E/D on PE snapshots @ H4) — Exact Decimal prec=50+
GOLDEN_FACILITY_MWH_RAW = Decimal("501.76628")
GOLDEN_CBAM_MWH_RAW = Decimal("41.294457198595287166434679084184733750754042059647")
GOLDEN_NON_CBAM_MWH_RAW = GOLDEN_FACILITY_MWH_RAW - GOLDEN_CBAM_MWH_RAW
GOLDEN_FACILITY_EM_RAW = Decimal("220.27539692")
GOLDEN_CBAM_EM_RAW = Decimal("18.128266710183331066064824117957098116581024464185")
GOLDEN_NON_CBAM_EM_RAW = GOLDEN_FACILITY_EM_RAW - GOLDEN_CBAM_EM_RAW

# PostgreSQL Numeric(36, 18) round-trip
GOLDEN_CBAM_MWH_RAW_STORED = Decimal("41.294457198595287166")
GOLDEN_FACILITY_MWH_RAW_STORED = Decimal("501.766280000000000000")
GOLDEN_CBAM_EM_RAW_STORED = Decimal("18.128266710183331066")
GOLDEN_FACILITY_EM_RAW_STORED = Decimal("220.275396920000000000")

GOLDEN_CBAM_MWH_FINAL = Decimal("41.29445720")
GOLDEN_FACILITY_MWH_FINAL = Decimal("501.76628000")
GOLDEN_CBAM_EM_FINAL = Decimal("18.12826671")
GOLDEN_FACILITY_EM_FINAL = Decimal("220.27539692")
GOLDEN_REMAINING = Decimal("0")

# Workbook product rows B19:B21 (math golden only; Ecotrace EXACT_MATCH uses E)
WORKBOOK_PRODUCT_TONNES = [
    Decimal("39.336"),
    Decimal("34.559"),
    Decimal("29.688"),
]
WORKBOOK_PRODUCT_ELEC_FINALS = {
    Decimal("39.336"): Decimal("15.68171195"),
    Decimal("34.559"): Decimal("13.77731043"),
    Decimal("29.688"): Decimal("11.83543482"),
}
WORKBOOK_PRODUCT_EM_FINALS = {
    Decimal("39.336"): Decimal("6.88427154"),
    Decimal("34.559"): Decimal("6.04823928"),
    Decimal("29.688"): Decimal("5.19575589"),
}

# Service seed uses monthly E as production qty (DEA pattern / EXACT_MATCH)
GOLDEN_PRODUCT_ELEC_FINALS_BY_E = {
    Decimal("39.34"): Decimal("15.68224680"),
    Decimal("29.69"): Decimal("11.83543232"),
    Decimal("34.56"): Decimal("13.77677808"),
}
GOLDEN_PRODUCT_EM_FINALS_BY_E = {
    Decimal("39.34"): Decimal("6.88450635"),
    Decimal("29.69"): Decimal("5.19575479"),
    Decimal("34.56"): Decimal("6.04800557"),
}


def _manual(value: Decimal = H4) -> PurchasedElectricityManualFactor:
    return PurchasedElectricityManualFactor(
        value=value,
        unit="tCO2e/MWh",
        source_name="Workbook H4",
        source_document="SKDM_Alokasyon_Sablon.xlsx",
        dataset_version="workbook-example",
        reference_description="Example EF without platform provenance seed",
        effective_date=date(2024, 1, 1),
    )


def seed_workbook_ready_ie_allocation(
    db: Session,
    user: User | None = None,
    organization: Organization | None = None,
    *,
    with_exported: bool = False,
    mix_mwh_unit: bool = False,
) -> tuple[User, Organization, object, object]:
    """Three workbook months: PE current results, D/E READY, production EXACT_MATCH."""
    user = user or admin(db)
    organization = organization or org(db)
    binding, installation = setup_binding(db, user, organization)
    for day, kwh, d, e in WORKBOOK_ELEC_MONTHS:
        qty = kwh
        unit = "kWh"
        if mix_mwh_unit and day.month == 8:
            qty = kwh / Decimal("1000")
            unit = "MWh"
        activity = activity_record_service.create_activity_record(
            db,
            user,
            organization.id,
            binding.id,
            ActivityRecordCreate(
                installation_profile_id=installation.id,
                activity_type="ELECTRICITY",
                activity_date=day,
                quantity=qty,
                unit=unit,
                data_source_type="PRIMARY",
            ),
        )
        req = PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            factor_source_mode="MANUAL",
            manual_factor=_manual(),
        )
        if with_exported and day.month == 7:
            req.exported_electricity_quantity = Decimal("5")
            req.exported_electricity_unit = "MWh"
        execute_purchased_electricity(db, user, organization.id, binding.id, req)
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
            db, organization.id, code=f"IEP-{day.month}-{uuid.uuid4().hex[:4]}"
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
    db.commit()
    return user, organization, binding, installation
