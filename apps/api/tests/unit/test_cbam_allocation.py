from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from tests.cbam_profile_helpers import create_active_ready_profile

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, ValidationAppError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    allocation_rule_service,
    allocation_service,
    installation_service,
    period_binding_service,
    production_record_service,
    purchased_input_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.allocation_math import (
    CALCULATION_VERSION,
    compute_allocated_quantity,
    compute_production_quantity_ratio,
    direct_assignment_ratio,
)
from ecotrace.modules.cbam.application.allocation_rule_service import (
    AllocationRuleCreate,
    AllocationRuleUpdate,
    AllocationRuleVersionRequest,
)
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
from ecotrace.modules.cbam.application.purchased_input_service import PurchasedInputCreate
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


def _setup(db, admin, org):
    facility = _facility(db, org.id)
    installation_service.create_installation(
        db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"P4A-{uuid.uuid4().hex[:8]}",
            name="P4A Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"P4A-{uuid.uuid4().hex[:6]}",
        name="P4A Period",
        period_type="custom",
        start_date=__import__("datetime").date(2029, 1, 1),
        end_date=__import__("datetime").date(2029, 3, 31),
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


def test_allocation_math_decimal_safe() -> None:
    assert direct_assignment_ratio() == Decimal("1")
    ratio = compute_production_quantity_ratio(numerator=Decimal("100"), denominator=Decimal("500"))
    assert ratio == Decimal("0.2")
    allocated = compute_allocated_quantity(source_quantity=Decimal("100"), allocation_ratio=ratio)
    assert allocated == Decimal("20")
    with pytest.raises(ValidationAppError):
        compute_production_quantity_ratio(numerator=Decimal("100"), denominator=Decimal("0"))
    with pytest.raises(ValidationAppError):
        compute_production_quantity_ratio(numerator=Decimal("600"), denominator=Decimal("500"))


def test_direct_assignment_and_production_ratio_flow(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)

    base = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            product_profile_version_id=profile.id,
            installation_profile_id=installation.id,
            quantity=Decimal("500"),
            unit="t",
        ),
    )
    target = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            product_profile_version_id=profile.id,
            installation_profile_id=installation.id,
            quantity=Decimal("100"),
            unit="t",
        ),
    )
    activity = activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="ELECTRICITY",
            quantity=Decimal("100"),
            unit="MWh",
            data_source_type="PRIMARY",
        ),
    )

    direct = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            installation_profile_id=installation.id,
            allocation_method="DIRECT_ASSIGNMENT",
            name="Direct electricity",
        ),
    )
    assert direct.allocation_ratio == Decimal("1")
    activated_direct = allocation_rule_service.activate_allocation_rule(
        seeded_db,
        admin,
        org.id,
        direct.id,
        AllocationRuleVersionRequest(row_version=direct.row_version),
    )
    assert activated_direct.status == "ACTIVE"
    direct_result = allocation_service.allocate_activity_record(
        seeded_db, admin, org.id, activated_direct.id, activity.id
    )
    assert direct_result.allocated_quantity == Decimal("100")
    assert direct_result.source_quantity == Decimal("100")
    assert direct_result.calculation_version == CALCULATION_VERSION

    allocation_rule_service.archive_allocation_rule(
        seeded_db,
        admin,
        org.id,
        activated_direct.id,
        AllocationRuleVersionRequest(row_version=activated_direct.row_version),
    )

    ratio_rule = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            installation_profile_id=installation.id,
            allocation_method="PRODUCTION_QUANTITY_RATIO",
            name="Prod ratio",
            numerator_production_record_id=target.id,
            denominator_production_record_id=base.id,
        ),
    )
    assert ratio_rule.allocation_ratio == Decimal("0.2")
    assert ratio_rule.numerator_quantity == Decimal("100")
    assert ratio_rule.denominator_quantity == Decimal("500")
    active_ratio = allocation_rule_service.activate_allocation_rule(
        seeded_db,
        admin,
        org.id,
        ratio_rule.id,
        AllocationRuleVersionRequest(row_version=ratio_rule.row_version),
    )
    result = allocation_service.allocate_activity_record(
        seeded_db, admin, org.id, active_ratio.id, activity.id
    )
    assert result.allocation_ratio == Decimal("0.2")
    assert result.allocated_quantity == Decimal("20")
    assert result.allocated_unit == "MWh"
    assert result.source_quantity == Decimal("100")

    audits = (
        seeded_db.execute(select(AuditLog).where(AuditLog.action == "cbam.allocation.executed"))
        .scalars()
        .all()
    )
    assert any(a.entity_id == str(result.id) for a in audits)


def test_production_ratio_validation_rejects(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    base = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            product_profile_version_id=profile.id,
            installation_profile_id=installation.id,
            quantity=Decimal("500"),
            unit="t",
        ),
    )
    target_kg = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            product_profile_version_id=profile.id,
            installation_profile_id=installation.id,
            quantity=Decimal("100"),
            unit="kg",
        ),
    )
    with pytest.raises(ValidationAppError):
        allocation_rule_service.create_allocation_rule(
            seeded_db,
            admin,
            org.id,
            binding.id,
            AllocationRuleCreate(
                installation_profile_id=installation.id,
                allocation_method="PRODUCTION_QUANTITY_RATIO",
                name="Bad units",
                numerator_production_record_id=target_kg.id,
                denominator_production_record_id=base.id,
            ),
        )
    oversized = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            product_profile_version_id=profile.id,
            installation_profile_id=installation.id,
            quantity=Decimal("600"),
            unit="t",
        ),
    )
    with pytest.raises(ValidationAppError):
        allocation_rule_service.create_allocation_rule(
            seeded_db,
            admin,
            org.id,
            binding.id,
            AllocationRuleCreate(
                installation_profile_id=installation.id,
                allocation_method="PRODUCTION_QUANTITY_RATIO",
                name="Oversized",
                numerator_production_record_id=oversized.id,
                denominator_production_record_id=base.id,
            ),
        )


def test_manual_ratio_bounds_and_rationale(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    for ratio in (Decimal("0"), Decimal("1"), Decimal("0.25")):
        rule = allocation_rule_service.create_allocation_rule(
            seeded_db,
            admin,
            org.id,
            binding.id,
            AllocationRuleCreate(
                installation_profile_id=installation.id,
                allocation_method="MANUAL_RATIO",
                name=f"Manual {ratio}",
                allocation_ratio=ratio,
                rationale="Uzman değerlendirmesi",
                source_reference="internal note",
            ),
        )
        assert rule.allocation_ratio == ratio
    with pytest.raises(ValidationAppError):
        allocation_rule_service.create_allocation_rule(
            seeded_db,
            admin,
            org.id,
            binding.id,
            AllocationRuleCreate(
                installation_profile_id=installation.id,
                allocation_method="MANUAL_RATIO",
                name="Bad low",
                allocation_ratio=Decimal("-0.1"),
                rationale="x",
                source_reference="y",
            ),
        )
    with pytest.raises(ValidationAppError):
        allocation_rule_service.create_allocation_rule(
            seeded_db,
            admin,
            org.id,
            binding.id,
            AllocationRuleCreate(
                installation_profile_id=installation.id,
                allocation_method="MANUAL_RATIO",
                name="Bad high",
                allocation_ratio=Decimal("1.1"),
                rationale="x",
                source_reference="y",
            ),
        )
    with pytest.raises(ValidationAppError):
        allocation_rule_service.create_allocation_rule(
            seeded_db,
            admin,
            org.id,
            binding.id,
            AllocationRuleCreate(
                installation_profile_id=installation.id,
                allocation_method="MANUAL_RATIO",
                name="No rationale",
                allocation_ratio=Decimal("0.5"),
                source_reference="y",
            ),
        )


def test_purchased_input_uses_consumed_not_purchased(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    with_consumed = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name="Steam",
            quantity=Decimal("200"),
            unit="t",
            consumed_quantity=Decimal("80"),
            consumed_unit="t",
        ),
    )
    without_consumed = purchased_input_service.create_purchased_input(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PurchasedInputCreate(
            installation_profile_id=installation.id,
            input_name="Coal",
            quantity=Decimal("50"),
            unit="t",
        ),
    )
    rule = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            installation_profile_id=installation.id,
            allocation_method="DIRECT_ASSIGNMENT",
            name="Purchased direct",
        ),
    )
    active = allocation_rule_service.activate_allocation_rule(
        seeded_db,
        admin,
        org.id,
        rule.id,
        AllocationRuleVersionRequest(row_version=rule.row_version),
    )
    result = allocation_service.allocate_purchased_input(
        seeded_db, admin, org.id, active.id, with_consumed.id
    )
    assert result.source_quantity == Decimal("80")
    assert result.allocated_quantity == Decimal("80")
    with pytest.raises(BusinessRuleError):
        allocation_service.allocate_purchased_input(
            seeded_db, admin, org.id, active.id, without_consumed.id
        )


def test_recalculate_supersedes_previous(seeded_db) -> None:
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
            activity_type="ELECTRICITY",
            quantity=Decimal("100"),
            unit="MWh",
            data_source_type="PRIMARY",
        ),
    )
    rule = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            installation_profile_id=installation.id,
            allocation_method="MANUAL_RATIO",
            name="Manual 25",
            allocation_ratio=Decimal("0.25"),
            rationale="test",
            source_reference="test",
        ),
    )
    active = allocation_rule_service.activate_allocation_rule(
        seeded_db,
        admin,
        org.id,
        rule.id,
        AllocationRuleVersionRequest(row_version=rule.row_version),
    )
    first = allocation_service.allocate_activity_record(
        seeded_db, admin, org.id, active.id, activity.id
    )
    assert first.allocated_quantity == Decimal("25")
    second = allocation_service.recalculate_allocation_result(seeded_db, admin, org.id, first.id)
    assert second.id != first.id
    assert second.is_current is True
    assert second.allocated_quantity == Decimal("25")
    from ecotrace.modules.cbam.infrastructure.models import CbamAllocationResult

    old = seeded_db.get(CbamAllocationResult, first.id)
    assert old is not None
    seeded_db.refresh(old)
    assert old.is_current is False
    assert old.superseded_at is not None


def test_stale_row_version_and_draft_only_update(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    rule = allocation_rule_service.create_allocation_rule(
        seeded_db,
        admin,
        org.id,
        binding.id,
        AllocationRuleCreate(
            installation_profile_id=installation.id,
            allocation_method="DIRECT_ASSIGNMENT",
            name="Draft rule",
        ),
    )
    with pytest.raises(ConflictError):
        allocation_rule_service.update_allocation_rule(
            seeded_db,
            admin,
            org.id,
            rule.id,
            AllocationRuleUpdate(row_version=999, name="Stale"),
        )
    active = allocation_rule_service.activate_allocation_rule(
        seeded_db,
        admin,
        org.id,
        rule.id,
        AllocationRuleVersionRequest(row_version=rule.row_version),
    )
    with pytest.raises(BusinessRuleError):
        allocation_rule_service.update_allocation_rule(
            seeded_db,
            admin,
            org.id,
            active.id,
            AllocationRuleUpdate(row_version=active.row_version, name="Nope"),
        )


def test_phase4a_has_no_forbidden_engine_imports() -> None:
    assert find_forbidden_imports_in_tree() == []


def test_phase4a_source_has_no_emission_calculation() -> None:
    api_root = Path(__file__).resolve().parents[2]
    src = api_root / "src" / "ecotrace"
    files = [
        src / "modules" / "cbam" / "application" / "allocation_math.py",
        src / "modules" / "cbam" / "application" / "allocation_rule_service.py",
        src / "modules" / "cbam" / "application" / "allocation_service.py",
    ]
    banned = (
        "ipcc",
        "defra",
        "epa_factor",
        "emission_factor",
        "co2e_factor",
        "embedded_emission_calc",
        "calculate_co2",
        "openpyxl",
        "xlsxwriter",
        "generate_excel",
        "cn_code",
        "shipment_allocation",
    )
    for path in files:
        text = path.read_text(encoding="utf-8").lower()
        for token in banned:
            assert token not in text, f"{path} contains banned token {token}"
    math_src = (src / "modules" / "cbam" / "application" / "allocation_math.py").read_text()
    assert "source_quantity * allocation_ratio" in math_src
    assert "emission_factor" not in math_src.lower()
    assert "co2" not in math_src.lower()
