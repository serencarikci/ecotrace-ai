from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from tests.cbam_profile_helpers import create_active_ready_profile

from ecotrace.core.exceptions import ConflictError, ValidationAppError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    installation_service,
    period_binding_service,
    production_record_service,
    purchased_input_service,
)
from ecotrace.modules.cbam.application.activity_record_service import (
    ActivityPropertyInput,
    ActivityRecordCreate,
    ActivityRecordUpdate,
    ActivityRecordVersionRequest,
)
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_input_service import (
    PurchasedInputCreate,
    PurchasedInputVersionRequest,
)
from ecotrace.modules.cbam.architecture_boundary import find_forbidden_imports_in_tree
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import AuditLog, User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


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


def _setup_binding(db, admin, org):
    facility = _facility(db, org.id)
    installation_service.create_installation(
        db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"P3-{uuid.uuid4().hex[:8]}",
            name="P3 Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"P3-{uuid.uuid4().hex[:6]}",
        name="P3 Period",
        period_type="custom",
        start_date=__import__("datetime").date(2028, 1, 1),
        end_date=__import__("datetime").date(2028, 3, 31),
        status="open",
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


def test_production_create_reject_zero_and_stale(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup_binding(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    with pytest.raises(ValidationAppError):
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=profile.id,
                quantity=Decimal("0"),
                unit="t",
            ),
        )
    created = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            quantity=Decimal("10"),
            unit="t",
        ),
    )
    assert created.status == "active"
    assert created.profile_link_status == "READY"
    with pytest.raises(ConflictError):
        production_record_service.update_production_record(
            seeded_db,
            admin,
            org.id,
            created.id,
            ProductionRecordUpdate(row_version=99, quantity=Decimal("11")),
        )
    archived = production_record_service.archive_production_record(
        seeded_db,
        admin,
        org.id,
        created.id,
        ProductionRecordVersionRequest(row_version=created.row_version),
    )
    assert archived.status == "archived"
    audit = seeded_db.execute(
        select(AuditLog).where(
            AuditLog.action == "cbam.production_record.created",
            AuditLog.entity_id == str(created.id),
        )
    ).scalar_one()
    assert audit.organization_id == org.id


def test_activity_types_units_and_primary_properties(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup_binding(seeded_db, admin, org)
    with pytest.raises(ValidationAppError):
        activity_record_service.create_activity_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ActivityRecordCreate(
                installation_profile_id=installation.id,
                activity_type="ELECTRICITY",
                quantity=Decimal("100"),
                unit="L",
                data_source_type="PRIMARY",
            ),
        )
    with pytest.raises(ValidationAppError):
        activity_record_service.create_activity_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ActivityRecordCreate(
                installation_profile_id=installation.id,
                activity_type="NOT_A_TYPE",
                quantity=Decimal("100"),
                unit="kWh",
                data_source_type="PRIMARY",
            ),
        )
    electricity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="ELECTRICITY",
            quantity=Decimal("12500"),
            unit="kWh",
            data_source_type="PRIMARY",
            source_reference="meter-1",
            properties=[
                ActivityPropertyInput(
                    property_code="NET_CALORIFIC_VALUE",
                    numeric_value=Decimal("1.1"),
                    unit="GJ",
                )
            ],
        ),
    )
    assert electricity.activity_group == "PURCHASED_ENERGY"
    assert len(electricity.properties) == 1
    gas = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="NATURAL_GAS",
            quantity=Decimal("50"),
            unit="m3",
            data_source_type="DEFAULT_REFERENCE",
        ),
    )
    assert gas.data_source_type == "DEFAULT_REFERENCE"
    diesel = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="DIESEL",
            quantity=Decimal("20"),
            unit="L",
            data_source_type="UNKNOWN",
        ),
    )
    assert diesel.activity_type == "DIESEL"
    steam = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="PURCHASED_STEAM",
            quantity=Decimal("5"),
            unit="GJ",
            data_source_type="PRIMARY",
        ),
    )
    assert steam.unit == "GJ"
    with pytest.raises(ConflictError):
        activity_record_service.update_activity_record(
            seeded_db,
            admin,
            org.id,
            electricity.id,
            ActivityRecordUpdate(row_version=0, notes="stale"),
        )
    archived = activity_record_service.archive_activity_record(
        seeded_db,
        admin,
        org.id,
        electricity.id,
        ActivityRecordVersionRequest(row_version=electricity.row_version),
    )
    assert archived.status == "archived"


def test_purchased_consumed_rules(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup_binding(seeded_db, admin, org)
    ok = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name="Anode material",
            quantity=Decimal("100"),
            unit="t",
            consumed_quantity=Decimal("30"),
            consumed_unit="t",
            embedded_emission_value=Decimal("1.2"),
            embedded_emission_unit="tCO2e/t",
            embedded_emission_source_type="PRIMARY",
        ),
    )
    assert ok.consumed_quantity == Decimal("30")
    equal = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name="Equal consume",
            quantity=Decimal("10"),
            unit="kg",
            consumed_quantity=Decimal("10"),
            consumed_unit="kg",
        ),
    )
    assert equal.consumed_quantity == Decimal("10")
    with pytest.raises(ValidationAppError):
        purchased_input_service.create_purchased_input(
            seeded_db,
            admin,
            org.id,
            binding.id,
            PurchasedInputCreate(
                installation_profile_id=installation.id,
                input_name="Over consume",
                quantity=Decimal("10"),
                unit="kg",
                consumed_quantity=Decimal("11"),
                consumed_unit="kg",
            ),
        )
    missing_ee = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name="No EE",
            quantity=Decimal("5"),
            unit="t",
            embedded_emission_source_type="NOT_PROVIDED",
        ),
    )
    assert missing_ee.embedded_emission_value is None
    archived = purchased_input_service.archive_purchased_input(
        seeded_db,
        admin,
        org.id,
        ok.id,
        PurchasedInputVersionRequest(row_version=ok.row_version),
    )
    assert archived.status == "archived"


def test_phase3_has_no_forbidden_engine_imports() -> None:
    findings = find_forbidden_imports_in_tree()
    assert findings == []


def test_phase3_source_has_no_emission_calculation_keywords() -> None:
    api_root = Path(__file__).resolve().parents[2]
    src = api_root / "src" / "ecotrace"
    files = list((src / "modules" / "cbam").rglob("*.py"))
    files.append(src / "api" / "v1" / "cbam.py")
    export_allow = {
        "export_storage.py",
        "export_template_service.py",
        "export_readiness_service.py",
        "export_context.py",
        "workbook_export_service.py",
        "internal_template_builder.py",
        "period_summary_service.py",
        "0013_cbam_excel_export.py",
        # Phase 12A Official SEE export (read-only sheet inspection / ZIP writer helpers)
        "writer.py",
        "leakage.py",
        "forensics.py",
        "parity.py",
        "package_writer.py",
        "package_inventory.py",
        "clearing.py",
        "recalc.py",
    }
    banned = (
        "apcc",
        "co2e_factor",
        "allocate_emission",
        "calculate_see",
        "xlsxwriter",
        "ipcc_lookup",
        "defra_lookup",
        "fetch_ipcc",
        "fetch_defra",
        "urllib.request",
    )
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path} contains banned token {token}"
        if path.name not in export_allow:
            assert "openpyxl" not in text, f"{path} contains banned token openpyxl"
        if path.name in {
            "production_record_service.py",
            "activity_record_service.py",
            "purchased_input_service.py",
            "catalogs.py",
        }:
            assert "ipcc" not in text
            assert "defra" not in text
