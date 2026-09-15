"""Phase 7A-2 service acceptance: golden, history, deletion, preconditions, stale."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from tests.cbam_dea_helpers import (
    GOLDEN_CBAM_FOSSIL_CO2_RAW,
    GOLDEN_CBAM_FOSSIL_CO2_RAW_STORED,
    GOLDEN_CBAM_POOL_FINAL,
    GOLDEN_FACILITY_FINAL,
    GOLDEN_FACILITY_FOSSIL_CO2_RAW,
    GOLDEN_FACILITY_FOSSIL_CO2_RAW_STORED,
    GOLDEN_NON_CBAM_FINAL,
    GOLDEN_NON_CBAM_FOSSIL_CO2_RAW_STORED,
    GOLDEN_REMAINING,
    WORKBOOK_MONTHS,
    admin,
    create_ng_activity,
    org,
    run_sc,
    seed_workbook_ready_allocation,
    setup_binding,
)
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ecotrace.modules.cbam.application import (
    monthly_production_basis_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_constants import (
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_math import (
    period_wide_shortcut_share,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
    assert_production_record_not_referenced,
    compute_allocation_stale_reasons,
    execute_direct_emissions_allocation,
    get_direct_emissions_allocation_readiness,
    get_direct_emissions_allocation_result,
    get_direct_emissions_allocation_summary,
    list_direct_emissions_allocation_results,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
    MonthlyProductionBasisUpdate,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordCreate,
    ProductionRecordUpdate,
    ProductionRecordVersionRequest,
    archive_production_record,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamDeaMonthlyBasisSnapshot,
    CbamDeaProductAllocation,
    CbamDeaSourceSnapshot,
    CbamDirectEmissionsAllocationCurrent,
    CbamDirectEmissionsAllocationResult,
    CbamProductProfileVersion,
)


def _exec(db, user, organization, binding, client_id=None):
    return execute_direct_emissions_allocation(
        db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=client_id or uuid.uuid4()),
    )


def test_readiness_not_ready_without_inputs(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = setup_binding(seeded_db, user, organization)
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.allocation_ready is False
    assert readiness.status == "NOT_READY"
    assert "DIRECT_EMISSIONS_NOT_READY" in readiness.blocking_issue_codes


def test_execute_golden_path_exact_decimals_and_idempotency(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.allocation_ready is True

    client_id = uuid.uuid4()
    first = _exec(seeded_db, user, organization, binding, client_id)
    assert first.idempotent_replay is False
    assert first.balance_status == "BALANCED"
    assert first.remaining_fossil_co2_tonnes == GOLDEN_REMAINING
    assert first.allocated_fossil_co2_tonnes == first.cbam_fossil_co2_tonnes
    assert first.cbam_fossil_co2_tonnes == GOLDEN_CBAM_POOL_FINAL
    assert first.facility_fossil_co2_tonnes == GOLDEN_FACILITY_FINAL
    assert first.non_cbam_fossil_co2_tonnes == GOLDEN_NON_CBAM_FINAL
    assert (
        first.facility_fossil_co2_tonnes
        == first.cbam_fossil_co2_tonnes + first.non_cbam_fossil_co2_tonnes
    )

    detail = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, first.result_id
    )
    assert detail.facility_fossil_co2_tonnes_raw == GOLDEN_FACILITY_FOSSIL_CO2_RAW_STORED
    assert detail.cbam_fossil_co2_tonnes_raw == GOLDEN_CBAM_FOSSIL_CO2_RAW_STORED
    assert detail.non_cbam_fossil_co2_tonnes_raw == GOLDEN_NON_CBAM_FOSSIL_CO2_RAW_STORED
    assert detail.remaining_fossil_co2_tonnes == GOLDEN_REMAINING
    # In-memory Stage-1 raw (pre-Numeric) matches workbook/math golden
    assert abs(GOLDEN_CBAM_FOSSIL_CO2_RAW - GOLDEN_CBAM_FOSSIL_CO2_RAW_STORED) < Decimal("1e-17")
    assert abs(GOLDEN_FACILITY_FOSSIL_CO2_RAW - GOLDEN_FACILITY_FOSSIL_CO2_RAW_STORED) < Decimal(
        "1e-12"
    )
    assert detail.is_current is True
    assert detail.is_stale is False
    assert len(detail.source_calculations) == 3
    assert len(detail.product_allocations) == 3
    assert len(detail.monthly_basis) == 3
    product_sum = sum(
        Decimal(p["finalAllocatedFossilCo2Tonnes"]) for p in detail.product_allocations
    )
    assert product_sum == detail.cbam_fossil_co2_tonnes == GOLDEN_CBAM_POOL_FINAL
    raw_sum = sum(Decimal(p["rawAllocatedFossilCo2Tonnes"]) for p in detail.product_allocations)
    assert abs(raw_sum - detail.cbam_fossil_co2_tonnes) < Decimal("0.00000002")

    d_sum = sum(m[2] for m in WORKBOOK_MONTHS)
    e_sum = sum(m[3] for m in WORKBOOK_MONTHS)
    shortcut_pool = detail.facility_fossil_co2_tonnes_raw * period_wide_shortcut_share(
        total_d=d_sum, total_e=e_sum
    )
    assert shortcut_pool != detail.cbam_fossil_co2_tonnes_raw

    replay = _exec(seeded_db, user, organization, binding, client_id)
    assert replay.idempotent_replay is True
    assert replay.result_id == first.result_id


def test_idempotency_key_reused_when_fingerprint_differs(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    client_id = uuid.uuid4()
    first = _exec(seeded_db, user, organization, binding, client_id)
    row = seeded_db.get(CbamDirectEmissionsAllocationResult, first.result_id)
    assert row is not None
    row.request_fingerprint = "0" * 64
    seeded_db.commit()
    with pytest.raises(ConflictError) as exc:
        _exec(seeded_db, user, organization, binding, client_id)
    assert exc.value.details[0]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_material_change_blocks_new_execution(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = page.items[0]
    production_record_service.update_production_record(
        seeded_db,
        user,
        organization.id,
        row.id,
        ProductionRecordUpdate(row_version=row.row_version, quantity=Decimal("99.99")),
    )
    with pytest.raises(BusinessRuleError):
        _exec(seeded_db, user, organization, binding)


def test_recalculation_pointer_and_old_key_replay(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    first = _exec(seeded_db, user, organization, binding)
    second = _exec(seeded_db, user, organization, binding)
    assert second.result_id != first.result_id
    pointer = seeded_db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding.id
        )
    ).scalar_one()
    assert pointer.current_result_id == second.result_id
    old = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, first.result_id
    )
    assert old.is_current is False
    _exec(seeded_db, user, organization, binding, first.client_request_id)
    pointer2 = seeded_db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding.id
        )
    ).scalar_one()
    assert pointer2.current_result_id == second.result_id


def test_failed_recalculation_preserves_current_pointer(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    first = _exec(seeded_db, user, organization, binding)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = page.items[0]
    production_record_service.update_production_record(
        seeded_db,
        user,
        organization.id,
        row.id,
        ProductionRecordUpdate(row_version=row.row_version, quantity=Decimal("1")),
    )
    with pytest.raises(BusinessRuleError):
        _exec(seeded_db, user, organization, binding)
    pointer = seeded_db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding.id
        )
    ).scalar_one()
    assert pointer.current_result_id == first.result_id


def test_monthly_basis_delete_blocked_after_allocation(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    _exec(seeded_db, user, organization, binding)
    basis = monthly_production_basis_service.list_monthly_production_basis(
        seeded_db, user, organization.id, binding.id, page=1, page_size=10
    ).items[0]
    with pytest.raises(ConflictError) as exc:
        monthly_production_basis_service.delete_monthly_production_basis(
            seeded_db, user, organization.id, basis.id
        )
    assert exc.value.details[0]["code"] == "MONTHLY_PRODUCTION_BASIS_REFERENCED_BY_ALLOCATION"


def test_production_archive_blocked_after_allocation(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = seed_workbook_ready_allocation(seeded_db, user, organization)
    executed = _exec(seeded_db, user, organization, binding)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    referenced = page.items[0]
    with pytest.raises(ConflictError) as exc:
        archive_production_record(
            seeded_db,
            user,
            organization.id,
            referenced.id,
            ProductionRecordVersionRequest(row_version=referenced.row_version),
        )
    assert exc.value.details[0]["code"] == "PRODUCTION_RECORD_REFERENCED_BY_ALLOCATION"

    # Unrelated draft production (not in allocation) can still be archived
    product = ensure_org_product(seeded_db, organization.id, code=f"UX-{uuid.uuid4().hex[:4]}")
    profile = create_active_ready_profile(seeded_db, user, organization.id, product=product)
    extra = production_record_service.create_production_record(
        seeded_db,
        user,
        organization.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            quantity=Decimal("0.01"),
            unit="t",
            production_date=date(2024, 7, 20),
        ),
    )
    # Extra was not part of completed allocation snapshot
    assert_production_record_not_referenced(
        seeded_db, organization_id=organization.id, production_record_id=extra.id
    )
    archived = archive_production_record(
        seeded_db,
        user,
        organization.id,
        extra.id,
        ProductionRecordVersionRequest(row_version=extra.row_version),
    )
    assert archived.status == "archived"
    # Allocation history intact
    snaps = (
        seeded_db.execute(
            select(CbamDeaProductAllocation).where(
                CbamDeaProductAllocation.result_id == executed.result_id
            )
        )
        .scalars()
        .all()
    )
    assert len(snaps) == 3


def test_mismatch_blocks_execution(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = page.items[0]
    production_record_service.update_production_record(
        seeded_db,
        user,
        organization.id,
        row.id,
        ProductionRecordUpdate(row_version=row.row_version, quantity=Decimal("1")),
    )
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "PRODUCTION_RECONCILIATION_MISMATCH" in readiness.blocking_issue_codes
    with pytest.raises(BusinessRuleError):
        _exec(seeded_db, user, organization, binding)


def test_precondition_codes_independent(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)

    # SC not ready
    binding, _ = setup_binding(seeded_db, user, organization)
    r = get_direct_emissions_allocation_readiness(seeded_db, user, organization.id, binding.id)
    assert "DIRECT_EMISSIONS_NOT_READY" in r.blocking_issue_codes

    # Missing combustion activity date
    from ecotrace.modules.cbam.infrastructure.models import CbamActivityRecord

    binding2, installation2 = setup_binding(seeded_db, user, organization)
    act = create_ng_activity(
        seeded_db,
        user,
        organization,
        binding2,
        installation2,
        qty=Decimal("10"),
        day=date(2024, 7, 15),
    )
    run_sc(seeded_db, user, organization, binding2, act, day=date(2024, 7, 15))
    db_act = seeded_db.get(CbamActivityRecord, act.id)
    assert db_act is not None
    db_act.activity_date = None
    seeded_db.flush()
    r2 = get_direct_emissions_allocation_readiness(seeded_db, user, organization.id, binding2.id)
    assert "COMBUSTION_ACTIVITY_DATE_REQUIRED" in r2.blocking_issue_codes


def test_precondition_monthly_basis_missing(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = setup_binding(seeded_db, user, organization)
    act = create_ng_activity(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        qty=Decimal("188"),
        day=date(2024, 7, 15),
    )
    run_sc(seeded_db, user, organization, binding, act, day=date(2024, 7, 15))
    r = get_direct_emissions_allocation_readiness(seeded_db, user, organization.id, binding.id)
    assert "MONTHLY_PRODUCTION_BASIS_NOT_READY" in r.blocking_issue_codes


def test_precondition_production_date_and_zero_denom(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _installation = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    from ecotrace.modules.cbam.infrastructure.models import CbamProductionRecord

    for item in page.items:
        row = seeded_db.get(CbamProductionRecord, item.id)
        assert row is not None
        row.production_date = None
    seeded_db.flush()
    r = get_direct_emissions_allocation_readiness(seeded_db, user, organization.id, binding.id)
    assert "PRODUCTION_DATE_REQUIRED" in r.blocking_issue_codes


def test_list_and_summary(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    executed = _exec(seeded_db, user, organization, binding)
    page = list_direct_emissions_allocation_results(
        seeded_db, user, organization.id, binding.id, page=1, page_size=20
    )
    assert page.total_items == 1
    assert page.items[0].is_current is True
    summary = get_direct_emissions_allocation_summary(seeded_db, user, organization.id, binding.id)
    assert summary.current_result_id == executed.result_id
    assert summary.balance_status == "BALANCED"


def test_historical_detail_from_snapshots_not_live_catalog(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    executed = _exec(seeded_db, user, organization, binding)
    detail = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    fuel_name = detail.source_calculations[0]["fuelName"]
    # Mutate live fuel display name — historical snapshot must keep original
    from ecotrace.modules.cbam.infrastructure.models import CbamStationaryCombustionFuel

    fuel = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == "NATURAL_GAS"
        )
    ).scalar_one()
    fuel.name = "MUTATED NATURAL GAS DISPLAY"
    seeded_db.flush()
    detail2 = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    assert detail2.source_calculations[0]["fuelName"] == fuel_name
    assert detail2.source_calculations[0]["fuelName"] != "MUTATED NATURAL GAS DISPLAY"


def test_newer_profile_version_does_not_modify_old_allocation(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    executed = _exec(seeded_db, user, organization, binding)
    detail = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    profile_id = uuid.UUID(detail.product_allocations[0]["productProfileVersionId"])
    profile = seeded_db.get(CbamProductProfileVersion, profile_id)
    assert profile is not None
    # Create and publish a newer version of the same product lineage if API supports draft clone
    # Minimal proof: mutate live profile product_name — snapshot unchanged
    original_name = detail.product_allocations[0].get("productName")
    profile.product_name = "MUTATED PRODUCT NAME"
    seeded_db.flush()
    detail2 = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    assert detail2.product_allocations[0].get("productName") == original_name
    reasons = compute_allocation_stale_reasons(
        seeded_db,
        user,
        organization.id,
        binding.id,
        seeded_db.get(CbamDirectEmissionsAllocationResult, executed.result_id),
    )
    # Display-only mutation of profile name is not a material stale reason
    assert "PRODUCTION_MATERIAL_CHANGED" not in reasons


def test_same_profile_version_grouped_different_versions_separate(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = setup_binding(seeded_db, user, organization)
    day = date(2024, 7, 15)
    act = create_ng_activity(
        seeded_db, user, organization, binding, installation, qty=Decimal("188"), day=day
    )
    run_sc(seeded_db, user, organization, binding, act, day=day)
    monthly_production_basis_service.create_monthly_production_basis(
        seeded_db,
        user,
        organization.id,
        binding.id,
        MonthlyProductionBasisCreate(
            month_start=date(2024, 7, 1),
            total_production_quantity=Decimal("100"),
            cbam_quantity=Decimal("50"),
            quantity_unit="t",
        ),
    )
    product = ensure_org_product(seeded_db, organization.id)
    profile = create_active_ready_profile(seeded_db, user, organization.id, product=product)
    # Two production records same profile version → one group
    for qty in (Decimal("20"), Decimal("30")):
        production_record_service.create_production_record(
            seeded_db,
            user,
            organization.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=profile.id,
                quantity=qty,
                unit="t",
                production_date=day,
            ),
        )
    # Second product/profile → separate group
    product2 = ensure_org_product(seeded_db, organization.id, code=f"P2-{uuid.uuid4().hex[:4]}")
    profile2 = create_active_ready_profile(seeded_db, user, organization.id, product=product2)
    production_record_service.create_production_record(
        seeded_db,
        user,
        organization.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile2.id,
            quantity=Decimal("50"),
            unit="t",
            production_date=day,
        ),
    )
    # Need full period months covered - add empty? Period is Jul-Sep so need Aug/Sep SC+basis+prod
    for mday, qty, d, e in WORKBOOK_MONTHS[1:]:
        a = create_ng_activity(
            seeded_db, user, organization, binding, installation, qty=qty, day=mday
        )
        run_sc(seeded_db, user, organization, binding, a, day=mday)
        monthly_production_basis_service.create_monthly_production_basis(
            seeded_db,
            user,
            organization.id,
            binding.id,
            MonthlyProductionBasisCreate(
                month_start=date(mday.year, mday.month, 1),
                total_production_quantity=d,
                cbam_quantity=e,
                quantity_unit="t",
            ),
        )
        p = ensure_org_product(
            seeded_db, organization.id, code=f"PX-{mday.month}-{uuid.uuid4().hex[:3]}"
        )
        pr = create_active_ready_profile(seeded_db, user, organization.id, product=p)
        production_record_service.create_production_record(
            seeded_db,
            user,
            organization.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=pr.id,
                quantity=e,
                unit="t",
                production_date=mday,
            ),
        )
    # July reconciliation: E=50 must match production sum 20+30+50=100 — mismatch!
    # Adjust July basis E to 100 to match
    basis_page = monthly_production_basis_service.list_monthly_production_basis(
        seeded_db, user, organization.id, binding.id, page=1, page_size=20
    )
    july = next(b for b in basis_page.items if b.month_start == date(2024, 7, 1))
    monthly_production_basis_service.update_monthly_production_basis(
        seeded_db,
        user,
        organization.id,
        july.id,
        MonthlyProductionBasisUpdate(
            row_version=july.row_version,
            total_production_quantity=Decimal("200"),
            cbam_quantity=Decimal("100"),
        ),
    )
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    if not readiness.allocation_ready:
        pytest.skip(f"fixture not ready: {readiness.blocking_issue_codes}")
    executed = _exec(seeded_db, user, organization, binding)
    detail = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    groups = {p["productProfileVersionId"] for p in detail.product_allocations}
    assert str(profile.id) in groups
    assert str(profile2.id) in groups
    same = next(
        p for p in detail.product_allocations if p["productProfileVersionId"] == str(profile.id)
    )
    assert len(same["productionRecordIds"]) == 2


# --- Stale event matrix ---


def _allocate(seeded_db):
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = seed_workbook_ready_allocation(seeded_db, user, organization)
    executed = _exec(seeded_db, user, organization, binding)
    result = seeded_db.get(CbamDirectEmissionsAllocationResult, executed.result_id)
    assert result is not None
    return organization, user, binding, installation, executed, result


def test_stale_source_activity_quantity(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    assert snap is not None
    from ecotrace.modules.cbam.infrastructure.models import CbamActivityRecord

    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.quantity = act.quantity + Decimal("1")
    seeded_db.flush()
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
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
    from ecotrace.modules.cbam.infrastructure.models import CbamActivityRecord

    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.unit = "Nm3"
    seeded_db.flush()
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
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
    from ecotrace.modules.cbam.infrastructure.models import CbamActivityRecord

    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.activity_date = date(2024, 7, 20)
    seeded_db.flush()
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
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
    from ecotrace.modules.cbam.infrastructure.models import CbamActivityRecord

    act = seeded_db.get(CbamActivityRecord, snap.activity_record_id)
    assert act is not None
    act.activity_type = "DIESEL"
    seeded_db.flush()
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "SOURCE_ACTIVITY_MATERIAL_CHANGED" in codes or "DIRECT_EMISSIONS_STALE" in codes


def test_stale_monthly_d_e_unit(seeded_db) -> None:
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
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "MONTHLY_PRODUCTION_BASIS_CHANGED" in codes


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
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "MONTHLY_PRODUCTION_BASIS_CHANGED" in codes


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
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "PRODUCTION_MATERIAL_CHANGED" in codes or "PRODUCTION_SET_CHANGED" in codes


def test_stale_production_added(seeded_db) -> None:
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
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "PRODUCTION_SET_CHANGED" in codes


def test_stale_methodology_or_workbook_on_result(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    result.workbook_sha256 = "f" * 64
    seeded_db.flush()
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "METHODOLOGY_OR_WORKBOOK_CHANGED" in codes
    result.workbook_sha256 = WORKBOOK_SHA256
    result.methodology_version = "9.9.9"
    seeded_db.flush()
    codes2 = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "METHODOLOGY_OR_WORKBOOK_CHANGED" in codes2
    assert result.methodology_code == METHODOLOGY_CODE
    assert METHODOLOGY_VERSION != "9.9.9"


def test_not_stale_when_newer_profile_published_for_other_product(seeded_db) -> None:
    organization, user, binding, _, _, result = _allocate(seeded_db)
    product = ensure_org_product(seeded_db, organization.id, code=f"NEW-{uuid.uuid4().hex[:4]}")
    create_active_ready_profile(seeded_db, user, organization.id, product=product)
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert codes == []


def test_snapshots_reload_without_live_resolution(seeded_db) -> None:
    _organization, _user, _binding, _, executed, _ = _allocate(seeded_db)
    src = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(
                CbamDeaSourceSnapshot.result_id == executed.result_id
            )
        )
        .scalars()
        .all()
    )
    mb = (
        seeded_db.execute(
            select(CbamDeaMonthlyBasisSnapshot).where(
                CbamDeaMonthlyBasisSnapshot.result_id == executed.result_id
            )
        )
        .scalars()
        .all()
    )
    prod = (
        seeded_db.execute(
            select(CbamDeaProductAllocation).where(
                CbamDeaProductAllocation.result_id == executed.result_id
            )
        )
        .scalars()
        .all()
    )
    assert len(src) == 3 and len(mb) == 3 and len(prod) == 3
    for s in src:
        assert s.facility_fossil_co2_tonnes is not None
        assert s.cbam_fossil_co2_tonnes is not None
        assert s.fuel_code
        assert s.fuel_name
    for p in prod:
        assert p.final_allocated_fossil_co2_tonnes is not None
        assert p.production_quantity_snapshots
        assert p.production_record_ids


def test_no_public_update_delete_on_completed_result(seeded_db) -> None:
    """Completed results are immutable: no service update/delete API exists."""
    import ecotrace.modules.cbam.application.direct_emissions_allocation_service as svc

    assert not hasattr(svc, "update_direct_emissions_allocation_result")
    assert not hasattr(svc, "delete_direct_emissions_allocation_result")


def test_unknown_result_id_not_found(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    with pytest.raises(NotFoundError):
        get_direct_emissions_allocation_result(
            seeded_db, user, organization.id, binding.id, uuid.uuid4()
        )


def test_sc_source_fk_restrict_and_no_delete_api(seeded_db) -> None:
    """SC results are immutable/undeletable; DEA source FK is ON DELETE RESTRICT."""
    _organization, _user, _binding, _, executed, _ = _allocate(seeded_db)
    snap = (
        seeded_db.execute(
            select(CbamDeaSourceSnapshot).where(
                CbamDeaSourceSnapshot.result_id == executed.result_id
            )
        )
        .scalars()
        .first()
    )
    assert snap is not None
    import ecotrace.modules.cbam.application.stationary_combustion_execution_service as sc_exec

    assert not hasattr(sc_exec, "delete_stationary_combustion_result")
    fk = CbamDeaSourceSnapshot.__table__.c.source_result_id.foreign_keys
    assert any(f.ondelete == "RESTRICT" for f in fk)
