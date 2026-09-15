"""Phase 8C service acceptance: golden, history, preconditions, stale, exported."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from tests.cbam_dea_helpers import admin, org, setup_binding
from tests.cbam_iea_helpers import (
    GOLDEN_CBAM_EM_FINAL,
    GOLDEN_CBAM_EM_RAW_STORED,
    GOLDEN_CBAM_MWH_FINAL,
    GOLDEN_CBAM_MWH_RAW_STORED,
    GOLDEN_FACILITY_EM_FINAL,
    GOLDEN_FACILITY_EM_RAW_STORED,
    GOLDEN_FACILITY_MWH_FINAL,
    GOLDEN_FACILITY_MWH_RAW_STORED,
    GOLDEN_PRODUCT_ELEC_FINALS_BY_E,
    GOLDEN_PRODUCT_EM_FINALS_BY_E,
    GOLDEN_REMAINING,
    WORKBOOK_ELEC_MONTHS,
    _manual,
    seed_workbook_ready_ie_allocation,
)

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ecotrace.modules.cbam.application import (
    monthly_production_basis_service,
    product_profile_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_constants import (
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_math import (
    period_wide_shortcut_share,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    IndirectEmissionsAllocationExecuteRequest,
    compute_allocation_stale_reasons,
    execute_indirect_emissions_allocation,
    get_indirect_emissions_allocation_readiness,
    get_indirect_emissions_allocation_result,
    get_indirect_emissions_allocation_summary,
    list_indirect_emissions_allocation_results,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisUpdate,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordVersionRequest,
)
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    PurchasedElectricityExecuteRequest,
    execute_purchased_electricity,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamIeaSourceSnapshot,
    CbamIndirectEmissionsAllocationCurrent,
    CbamIndirectEmissionsAllocationResult,
    CbamProductionRecord,
    CbamProductProfileVersion,
)


def _exec(db, user, organization, binding, client_id=None):
    return execute_indirect_emissions_allocation(
        db,
        user,
        organization.id,
        binding.id,
        IndirectEmissionsAllocationExecuteRequest(client_request_id=client_id or uuid.uuid4()),
    )


def test_readiness_not_ready_without_inputs(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = setup_binding(seeded_db, user, organization)
    readiness = get_indirect_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.allocation_ready is False
    assert readiness.status == "NOT_READY"
    assert "INDIRECT_EMISSIONS_NOT_READY" in readiness.blocking_issue_codes


def test_execute_golden_path_balances_and_idempotency(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    readiness = get_indirect_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.allocation_ready is True

    client_id = uuid.uuid4()
    first = _exec(seeded_db, user, organization, binding, client_id)
    assert first.idempotent_replay is False
    assert first.balance_status == "BALANCED"
    assert first.remaining_electricity_mwh == GOLDEN_REMAINING
    assert first.remaining_indirect_emissions_tco2e == GOLDEN_REMAINING
    assert first.cbam_electricity_mwh == GOLDEN_CBAM_MWH_FINAL
    assert first.facility_electricity_mwh == GOLDEN_FACILITY_MWH_FINAL
    assert first.cbam_indirect_emissions_tco2e == GOLDEN_CBAM_EM_FINAL
    assert first.facility_indirect_emissions_tco2e == GOLDEN_FACILITY_EM_FINAL
    assert first.allocated_electricity_mwh == first.cbam_electricity_mwh
    assert first.allocated_indirect_emissions_tco2e == first.cbam_indirect_emissions_tco2e
    assert (
        first.facility_electricity_mwh
        == first.cbam_electricity_mwh + first.non_cbam_electricity_mwh
    )
    assert (
        first.facility_indirect_emissions_tco2e
        == first.cbam_indirect_emissions_tco2e + first.non_cbam_indirect_emissions_tco2e
    )
    assert first.exported_electricity_mwh is None

    detail = get_indirect_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, first.result_id
    )
    assert detail.facility_electricity_mwh_raw == GOLDEN_FACILITY_MWH_RAW_STORED
    assert detail.cbam_electricity_mwh_raw == GOLDEN_CBAM_MWH_RAW_STORED
    assert detail.facility_indirect_emissions_tco2e_raw == GOLDEN_FACILITY_EM_RAW_STORED
    assert detail.cbam_indirect_emissions_tco2e_raw == GOLDEN_CBAM_EM_RAW_STORED
    assert detail.is_current is True
    assert detail.is_stale is False
    assert len(detail.sources) == 3
    assert len(detail.products) == 3
    assert len(detail.monthly_basis) == 3
    assert detail.methodology_code == METHODOLOGY_CODE
    assert detail.methodology_version == METHODOLOGY_VERSION
    assert detail.workbook_sha256 == WORKBOOK_SHA256

    elec_sum = sum(Decimal(p["finalAllocatedElectricityMwh"]) for p in detail.products)
    em_sum = sum(Decimal(p["finalAllocatedIndirectEmissionsTco2e"]) for p in detail.products)
    assert elec_sum == detail.cbam_electricity_mwh == GOLDEN_CBAM_MWH_FINAL
    assert em_sum == detail.cbam_indirect_emissions_tco2e == GOLDEN_CBAM_EM_FINAL

    for p in detail.products:
        qty = Decimal(p["normalizedQuantityTonnes"])
        assert Decimal(p["finalAllocatedElectricityMwh"]) == GOLDEN_PRODUCT_ELEC_FINALS_BY_E[qty]
        assert (
            Decimal(p["finalAllocatedIndirectEmissionsTco2e"]) == GOLDEN_PRODUCT_EM_FINALS_BY_E[qty]
        )

    d_sum = sum(m[2] for m in WORKBOOK_ELEC_MONTHS)
    e_sum = sum(m[3] for m in WORKBOOK_ELEC_MONTHS)
    shortcut = detail.facility_electricity_mwh_raw * period_wide_shortcut_share(
        total_d=d_sum, total_e=e_sum
    )
    assert shortcut != detail.cbam_electricity_mwh_raw

    replay = _exec(seeded_db, user, organization, binding, client_id)
    assert replay.idempotent_replay is True
    assert replay.result_id == first.result_id


def test_exported_electricity_separate_not_in_pool(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(
        seeded_db, with_exported=True
    )
    executed = _exec(seeded_db, user, organization, binding)
    assert executed.exported_electricity_mwh == Decimal("5")
    assert executed.cbam_electricity_mwh == GOLDEN_CBAM_MWH_FINAL
    assert executed.facility_electricity_mwh == GOLDEN_FACILITY_MWH_FINAL
    detail = get_indirect_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    assert any(
        s.get("exportedElectricityMwh") is not None
        and Decimal(str(s["exportedElectricityMwh"])) == Decimal("5")
        for s in detail.sources
    )
    product_em = sum(Decimal(p["finalAllocatedIndirectEmissionsTco2e"]) for p in detail.products)
    assert product_em == detail.cbam_indirect_emissions_tco2e


def test_mix_kwh_mwh_source_snapshots(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db, mix_mwh_unit=True)
    executed = _exec(seeded_db, user, organization, binding)
    assert executed.cbam_electricity_mwh == GOLDEN_CBAM_MWH_FINAL
    detail = get_indirect_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    units = {s["activityUnit"] for s in detail.sources}
    assert units == {"kWh", "MWh"}


def test_current_history_and_failed_recalc_preserves_current(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    first = _exec(seeded_db, user, organization, binding)
    second = _exec(seeded_db, user, organization, binding, uuid.uuid4())
    assert second.result_id != first.result_id

    listed = list_indirect_emissions_allocation_results(
        seeded_db, user, organization.id, binding.id, page=1, page_size=10
    )
    assert listed.total_items == 2
    currents = [i for i in listed.items if i.is_current]
    assert len(currents) == 1
    assert currents[0].result_id == second.result_id

    detail = get_indirect_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, second.result_id
    )
    prod_ids: set[str] = set()
    for p in detail.products:
        prod_ids.update(p["productionRecordIds"])
    for pid in prod_ids:
        row = production_record_service.get_production_record(
            seeded_db, user, organization.id, uuid.UUID(pid)
        )
        production_record_service.archive_production_record(
            seeded_db,
            user,
            organization.id,
            uuid.UUID(pid),
            ProductionRecordVersionRequest(row_version=row.row_version),
        )

    with pytest.raises(BusinessRuleError) as exc:
        _exec(seeded_db, user, organization, binding, uuid.uuid4())
    assert any(d.get("code") == "NO_ELIGIBLE_PRODUCTION" for d in (exc.value.details or []))

    pointer = seeded_db.execute(
        select(CbamIndirectEmissionsAllocationCurrent).where(
            CbamIndirectEmissionsAllocationCurrent.reporting_period_binding_id == binding.id
        )
    ).scalar_one()
    assert pointer.current_result_id == second.result_id


def test_idempotency_conflict_on_changed_inputs(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    cid = uuid.uuid4()
    _exec(seeded_db, user, organization, binding, cid)
    act = (
        seeded_db.execute(
            select(CbamActivityRecord).where(
                CbamActivityRecord.reporting_period_binding_id == binding.id
            )
        )
        .scalars()
        .first()
    )
    assert act is not None
    execute_purchased_electricity(
        seeded_db,
        user,
        organization.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=act.id,
            factor_source_mode="MANUAL",
            manual_factor=_manual(Decimal("0.5")),
        ),
    )
    with pytest.raises(ConflictError) as exc:
        _exec(seeded_db, user, organization, binding, cid)
    assert any(d.get("code") == "IDEMPOTENCY_KEY_REUSED" for d in (exc.value.details or []))


def test_stale_on_factor_change(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    executed = _exec(seeded_db, user, organization, binding)
    result = seeded_db.get(CbamIndirectEmissionsAllocationResult, executed.result_id)
    assert result is not None
    snap = (
        seeded_db.execute(
            select(CbamIeaSourceSnapshot).where(CbamIeaSourceSnapshot.result_id == result.id)
        )
        .scalars()
        .first()
    )
    assert snap is not None
    execute_purchased_electricity(
        seeded_db,
        user,
        organization.id,
        binding.id,
        PurchasedElectricityExecuteRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=snap.activity_record_id,
            factor_source_mode="MANUAL",
            manual_factor=_manual(Decimal("0.5")),
        ),
    )
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "SOURCE_CURRENT_RESULT_CHANGED" in codes or "INDIRECT_EMISSIONS_STALE" in codes


def test_not_stale_newer_profile_published(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    executed = _exec(seeded_db, user, organization, binding)
    result = seeded_db.get(CbamIndirectEmissionsAllocationResult, executed.result_id)
    assert result is not None
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None and row.product_profile_version_id is not None
    old_profile = seeded_db.get(CbamProductProfileVersion, row.product_profile_version_id)
    assert old_profile is not None
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
    assert (
        compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result) == []
    )


def test_stale_on_monthly_basis_change(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    executed = _exec(seeded_db, user, organization, binding)
    result = seeded_db.get(CbamIndirectEmissionsAllocationResult, executed.result_id)
    assert result is not None
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
            total_production_quantity=basis.total_production_quantity + Decimal("10"),
        ),
    )
    codes = compute_allocation_stale_reasons(seeded_db, user, organization.id, binding.id, result)
    assert "MONTHLY_PRODUCTION_BASIS_CHANGED" in codes


def test_blocks_reconciliation_mismatch(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
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
            cbam_quantity=basis.cbam_quantity + Decimal("1"),
        ),
    )
    readiness = get_indirect_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.allocation_ready is False
    assert "PRODUCTION_RECONCILIATION_MISMATCH" in readiness.blocking_issue_codes


def test_blocks_missing_activity_date(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    act = (
        seeded_db.execute(
            select(CbamActivityRecord).where(
                CbamActivityRecord.reporting_period_binding_id == binding.id
            )
        )
        .scalars()
        .first()
    )
    assert act is not None
    act.activity_date = None
    seeded_db.flush()
    readiness = get_indirect_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert readiness.allocation_ready is False
    assert any(
        c in readiness.blocking_issue_codes
        for c in (
            "ELECTRICITY_ACTIVITY_DATE_REQUIRED",
            "INDIRECT_EMISSIONS_NOT_READY",
            "INDIRECT_EMISSIONS_STALE",
        )
    )


def test_immutable_snapshot_reload(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    executed = _exec(seeded_db, user, organization, binding)
    detail1 = get_indirect_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    snap = (
        seeded_db.execute(
            select(CbamIeaSourceSnapshot).where(
                CbamIeaSourceSnapshot.result_id == executed.result_id
            )
        )
        .scalars()
        .first()
    )
    assert snap is not None
    stored_factor = snap.factor_value
    detail2 = get_indirect_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    assert any(s.get("factorValue") == str(stored_factor) for s in detail2.sources)
    assert detail1.cbam_electricity_mwh == detail2.cbam_electricity_mwh
    assert detail1.products == detail2.products


def test_summary_authoritative(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(
        seeded_db, with_exported=True
    )
    executed = _exec(seeded_db, user, organization, binding)
    summary = get_indirect_emissions_allocation_summary(
        seeded_db, user, organization.id, binding.id
    )
    assert summary.current_result_id == executed.result_id
    assert summary.facility_electricity_mwh == GOLDEN_FACILITY_MWH_FINAL
    assert summary.cbam_electricity_mwh == GOLDEN_CBAM_MWH_FINAL
    assert summary.cbam_indirect_emissions_tco2e == GOLDEN_CBAM_EM_FINAL
    assert summary.exported_electricity_mwh == Decimal("5")
    assert summary.balance_status == "BALANCED"
    assert len(summary.totals_by_month) == 3
    assert len(summary.totals_by_product_profile) == 3


def test_tenant_isolation(seeded_db) -> None:
    user, organization, binding, _ = seed_workbook_ready_ie_allocation(seeded_db)
    executed = _exec(seeded_db, user, organization, binding)
    with pytest.raises(NotFoundError):
        get_indirect_emissions_allocation_result(
            seeded_db, user, uuid.uuid4(), binding.id, executed.result_id
        )
