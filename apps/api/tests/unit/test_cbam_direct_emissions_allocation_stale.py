"""Phase 7A-2+ complete stale-event matrix (independent cases)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from tests.cbam_dea_helpers import (
    admin,
    org,
    run_sc,
    seed_workbook_ready_allocation,
)
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.modules.cbam.application import (
    monthly_production_basis_service,
    product_profile_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_constants import (
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
    compute_allocation_stale_reasons,
    execute_direct_emissions_allocation,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisUpdate,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordCreate,
    ProductionRecordUpdate,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamDeaSourceSnapshot,
    CbamDirectEmissionsAllocationResult,
    CbamProductionRecord,
    CbamProductProfileVersion,
    CbamStationaryCombustionFuel,
)


def _allocate(db):
    organization = org(db)
    user = admin(db)
    binding, installation = seed_workbook_ready_allocation(db, user, organization)
    executed = execute_direct_emissions_allocation(
        db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    result = db.get(CbamDirectEmissionsAllocationResult, executed.result_id)
    assert result is not None
    return organization, user, binding, installation, executed, result


def _codes(db, user, organization, binding, result):
    return compute_allocation_stale_reasons(db, user, organization.id, binding.id, result)


def test_stale_sc_current_pointer_changes(seeded_db) -> None:
    organization, user, binding, _installation, _, result = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    assert snap is not None
    # New SC execution for same activity replaces current pointer
    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    run_sc(seeded_db, user, organization, binding, act, day=act.activity_date)
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "SOURCE_CURRENT_RESULT_CHANGED" in codes


def test_stale_source_activity_quantity(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.quantity = act.quantity + Decimal("1")
    seeded_db.flush()
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "SOURCE_ACTIVITY_MATERIAL_CHANGED" in codes or "DIRECT_EMISSIONS_STALE" in codes


def test_stale_source_activity_unit(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.unit = "Nm3"
    seeded_db.flush()
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "SOURCE_ACTIVITY_MATERIAL_CHANGED" in codes or "DIRECT_EMISSIONS_STALE" in codes


def test_stale_source_activity_date(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.activity_date = date(2024, 7, 28)
    seeded_db.flush()
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "SOURCE_ACTIVITY_MATERIAL_CHANGED" in codes or "DIRECT_EMISSIONS_STALE" in codes


def test_stale_source_fuel_identity(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.activity_type = "DIESEL"
    seeded_db.flush()
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "SOURCE_ACTIVITY_MATERIAL_CHANGED" in codes or "DIRECT_EMISSIONS_STALE" in codes


def test_stale_monthly_d_change(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    basis = monthly_production_basis_service.list_monthly_production_basis(
        seeded_db, user, organization.id, binding.id, page=1, page_size=10
    ).items[0]
    monthly_production_basis_service.update_monthly_production_basis(
        seeded_db,
        user,
        organization.id,
        basis.id,
        MonthlyProductionBasisUpdate(
            row_version=basis.row_version,
            total_production_quantity=basis.total_production_quantity + Decimal("1"),
        ),
    )
    assert "MONTHLY_PRODUCTION_BASIS_CHANGED" in _codes(
        seeded_db, user, organization, binding, result
    )


def test_stale_monthly_e_change(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    basis = monthly_production_basis_service.list_monthly_production_basis(
        seeded_db, user, organization.id, binding.id, page=1, page_size=10
    ).items[0]
    monthly_production_basis_service.update_monthly_production_basis(
        seeded_db,
        user,
        organization.id,
        basis.id,
        MonthlyProductionBasisUpdate(
            row_version=basis.row_version,
            cbam_quantity=basis.cbam_quantity + Decimal("0.01"),
        ),
    )
    assert "MONTHLY_PRODUCTION_BASIS_CHANGED" in _codes(
        seeded_db, user, organization, binding, result
    )


def test_stale_monthly_unit_change(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    from ecotrace.modules.cbam.infrastructure.models import CbamMonthlyProductionBasis

    basis = seeded_db.execute(
        select(CbamMonthlyProductionBasis)
        .where(CbamMonthlyProductionBasis.reporting_period_binding_id == binding.id)
        .limit(1)
    ).scalar_one()
    basis.quantity_unit = "kg"
    basis.row_version += 1
    seeded_db.flush()
    assert "MONTHLY_PRODUCTION_BASIS_CHANGED" in _codes(
        seeded_db, user, organization, binding, result
    )


def test_stale_production_quantity(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = page.items[0]
    production_record_service.update_production_record(
        seeded_db,
        user,
        organization.id,
        row.id,
        ProductionRecordUpdate(
            row_version=row.row_version, quantity=row.quantity + Decimal("0.01")
        ),
    )
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "PRODUCTION_MATERIAL_CHANGED" in codes or "PRODUCTION_SET_CHANGED" in codes


def test_stale_production_unit(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None
    row.unit = "kg"
    seeded_db.flush()
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "PRODUCTION_MATERIAL_CHANGED" in codes


def test_stale_production_date(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = page.items[0]
    production_record_service.update_production_record(
        seeded_db,
        user,
        organization.id,
        row.id,
        ProductionRecordUpdate(row_version=row.row_version, production_date=date(2024, 7, 28)),
    )
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "PRODUCTION_MATERIAL_CHANGED" in codes


def test_stale_production_record_added(seeded_db) -> None:
    organization, user, binding, installation, _, result = _allocate(seeded_db)
    product = ensure_org_product(seeded_db, organization.id, code=f"ADD-{uuid.uuid4().hex[:4]}")
    profile = create_active_ready_profile(seeded_db, user, organization.id, product=product)
    production_record_service.create_production_record(
        seeded_db,
        user,
        organization.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            quantity=Decimal("1"),
            unit="t",
            production_date=date(2024, 7, 16),
        ),
    )
    assert "PRODUCTION_SET_CHANGED" in _codes(seeded_db, user, organization, binding, result)


def test_stale_production_record_archived(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None
    # Bypass archive guard to simulate removal path for stale detection
    row.status = "archived"
    seeded_db.flush()
    assert "PRODUCTION_SET_CHANGED" in _codes(seeded_db, user, organization, binding, result)


def test_stale_linked_product_profile_version_changes(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None
    new_product = ensure_org_product(seeded_db, organization.id, code=f"REL-{uuid.uuid4().hex[:4]}")
    new_profile = create_active_ready_profile(seeded_db, user, organization.id, product=new_product)
    row.product_profile_version_id = new_profile.id
    seeded_db.flush()
    codes = _codes(seeded_db, user, organization, binding, result)
    assert "PRODUCTION_MATERIAL_CHANGED" in codes or "PRODUCTION_SET_CHANGED" in codes


def test_stale_profile_link_becomes_invalid(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None and row.product_profile_version_id is not None
    profile = seeded_db.get(CbamProductProfileVersion, row.product_profile_version_id)
    assert profile is not None
    profile.classification_ready = False
    seeded_db.flush()
    assert "PRODUCTION_PROFILE_LINK_INVALID" in _codes(
        seeded_db, user, organization, binding, result
    )


def test_stale_methodology_version_changes(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    result.methodology_version = "9.9.9"
    seeded_db.flush()
    assert "METHODOLOGY_OR_WORKBOOK_CHANGED" in _codes(
        seeded_db, user, organization, binding, result
    )


def test_stale_workbook_checksum_changes(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    result.workbook_sha256 = "a" * 64
    seeded_db.flush()
    assert "METHODOLOGY_OR_WORKBOOK_CHANGED" in _codes(
        seeded_db, user, organization, binding, result
    )
    assert result.workbook_sha256 != WORKBOOK_SHA256


def test_not_stale_newer_profile_published(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None and row.product_profile_version_id is not None
    old_profile = seeded_db.get(CbamProductProfileVersion, row.product_profile_version_id)
    assert old_profile is not None
    # Publish a newer version for the same product; production still points at old.
    draft = product_profile_service.create_product_profile(
        seeded_db,
        user,
        organization.id,
        ProductProfileCreate(
            product_id=old_profile.product_id,
            product_name=old_profile.product_name or "x",
            cn_code=old_profile.cn_normalized_code or "73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="TR-TEST-002",
            percent_mn=Decimal("40"),
            percent_cr=Decimal("20"),
            percent_ni=Decimal("10"),
            percent_other_alloys=Decimal("10"),
            percent_other_materials=Decimal("20"),
        ),
    )
    product_profile_service.publish_product_profile(
        seeded_db,
        user,
        organization.id,
        draft.id,
        ProductProfileVersionRequest(row_version=draft.row_version),
    )
    seeded_db.refresh(old_profile)
    assert old_profile.status == "superseded"
    assert _codes(seeded_db, user, organization, binding, result) == []


def test_not_stale_outdated_but_valid_profile(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None and row.product_profile_version_id is not None
    profile = seeded_db.get(CbamProductProfileVersion, row.product_profile_version_id)
    assert profile is not None
    profile.status = "superseded"
    seeded_db.flush()
    assert _codes(seeded_db, user, organization, binding, result) == []


def test_not_stale_display_only_fuel_and_product_name(seeded_db) -> None:
    organization, user, binding, _, executed, result = _allocate(seeded_db)
    fuel = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == "NATURAL_GAS"
        )
    ).scalar_one()
    fuel.name = "DISPLAY ONLY FUEL NAME"
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None and row.product_profile_version_id is not None
    profile = seeded_db.get(CbamProductProfileVersion, row.product_profile_version_id)
    assert profile is not None
    profile.product_name = "DISPLAY ONLY PRODUCT"
    seeded_db.flush()
    assert _codes(seeded_db, user, organization, binding, result) == []
    # Historical detail still shows original snapshot names
    from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
        get_direct_emissions_allocation_result,
    )

    detail = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    assert detail.source_calculations[0]["fuelName"] != "DISPLAY ONLY FUEL NAME"
    assert detail.product_allocations[0]["productName"] != "DISPLAY ONLY PRODUCT"
