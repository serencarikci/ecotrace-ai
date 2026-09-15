"""Phase 7A-2+ integrity: unbalanced guard, JSONB snapshots, query bounds."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import event, select, text
from sqlalchemy.engine import Engine
from tests.cbam_dea_helpers import (
    admin,
    create_ng_activity,
    org,
    run_sc,
    seed_workbook_ready_allocation,
    setup_binding,
)
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application import (
    monthly_production_basis_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_math import (
    ProductAllocationRow,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
    execute_direct_emissions_allocation,
    get_direct_emissions_allocation_result,
    list_direct_emissions_allocation_results,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisCreate,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordCreate,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamDeaProductAllocation,
    CbamDirectEmissionsAllocationCurrent,
    CbamDirectEmissionsAllocationResult,
    CbamProductionRecord,
)


def test_unbalanced_allocation_cannot_complete_or_become_current(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    first = execute_direct_emissions_allocation(
        seeded_db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    pointer_before = seeded_db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding.id
        )
    ).scalar_one()
    assert pointer_before.current_result_id == first.result_id
    result_count_before = len(
        seeded_db.execute(select(CbamDirectEmissionsAllocationResult)).scalars().all()
    )

    def unbalanced_allocate(*, pool_raw, groups):
        pool_final = Decimal("1.00000000")
        gid = groups[0][0]
        return pool_final, [
            ProductAllocationRow(
                group_id=gid,
                quantity=groups[0][1],
                share=Decimal("1"),
                raw_allocated=Decimal("0.5"),
                final_allocated=Decimal("0.50000000"),
                rounding_adjustment=Decimal("0"),
            )
        ]

    client_id = uuid.uuid4()
    with (
        patch(
            "ecotrace.modules.cbam.application.direct_emissions_allocation_service."
            "allocate_pool_with_largest_remainder",
            side_effect=unbalanced_allocate,
        ),
        pytest.raises(BusinessRuleError) as exc,
    ):
        execute_direct_emissions_allocation(
            seeded_db,
            user,
            organization.id,
            binding.id,
            DirectEmissionsAllocationExecuteRequest(client_request_id=client_id),
        )
    assert any(d.get("code") == "UNBALANCED" for d in (exc.value.details or []))
    assert (
        len(seeded_db.execute(select(CbamDirectEmissionsAllocationResult)).scalars().all())
        == result_count_before
    )
    pointer_after = seeded_db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding.id
        )
    ).scalar_one()
    assert pointer_after.current_result_id == first.result_id
    assert (
        seeded_db.execute(
            select(CbamDirectEmissionsAllocationResult).where(
                CbamDirectEmissionsAllocationResult.client_request_id == client_id
            )
        ).scalar_one_or_none()
        is None
    )


def test_pg_rejects_balanced_with_nonzero_remaining(seeded_db) -> None:
    """Meaningful CHECK: BALANCED ⇒ remaining = 0 (create_all / model parity)."""
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    with pytest.raises(Exception) as exc:
        seeded_db.execute(
            text(
                """
                INSERT INTO cbam_direct_emissions_allocation_results (
                    id, organization_id, reporting_period_binding_id,
                    methodology_code, methodology_version, workbook_filename,
                    workbook_sha256, workbook_formula_refs, client_request_id,
                    request_fingerprint, status, balance_status,
                    facility_fossil_co2_tonnes_raw, cbam_fossil_co2_tonnes_raw,
                    non_cbam_fossil_co2_tonnes_raw,
                    facility_fossil_co2_tonnes, cbam_fossil_co2_tonnes,
                    non_cbam_fossil_co2_tonnes, allocated_fossil_co2_tonnes,
                    remaining_fossil_co2_tonnes, result_unit, workbook_reporting_unit,
                    workbook_gas, workbook_gwp, workbook_gwp_factor,
                    source_result_count, month_count, fuel_count,
                    participating_production_record_count, product_profile_group_count
                ) VALUES (
                    :id, :org, :binding,
                    'STATIONARY_COMBUSTION_DIRECT_EMISSIONS_ALLOCATION_V1', '1.0.0', 'x.xlsx',
                    :sha, 'refs', :cid,
                    :fp, 'COMPLETED', 'BALANCED',
                    1, 1, 0,
                    1, 1, 0, 0.5,
                    0.5, 'tCO2', 'tCO2e',
                    'CO2', '1', '1',
                    1, 1, 1, 1, 1
                )
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "org": str(organization.id),
                "binding": str(binding.id),
                "sha": "b" * 64,
                "cid": str(uuid.uuid4()),
                "fp": "c" * 64,
            },
        )
        seeded_db.flush()
    seeded_db.rollback()
    msg = str(exc.value).lower()
    assert "balanced_zero_remaining" in msg or "check" in msg


def test_jsonb_production_snapshots_complete_and_deterministic(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = setup_binding(seeded_db, user, organization)
    from tests.cbam_dea_helpers import WORKBOOK_MONTHS

    day = date(2024, 7, 15)
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
    product = ensure_org_product(seeded_db, organization.id, code=f"GRP-{uuid.uuid4().hex[:4]}")
    profile = create_active_ready_profile(seeded_db, user, organization.id, product=product)
    ids: list[str] = []
    for qty in (Decimal("20.5"), Decimal("29.5")):
        rec = production_record_service.create_production_record(
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
        ids.append(str(rec.id))

    executed = execute_direct_emissions_allocation(
        seeded_db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    alloc = seeded_db.execute(
        select(CbamDeaProductAllocation).where(
            CbamDeaProductAllocation.result_id == executed.result_id,
            CbamDeaProductAllocation.product_profile_version_id == profile.id,
        )
    ).scalar_one()
    assert alloc.production_record_ids == sorted(ids)
    snaps = alloc.production_quantity_snapshots
    assert len(snaps) == 2
    assert [s["productionRecordId"] for s in snaps] == sorted(ids)
    for s in snaps:
        assert {
            "productionRecordId",
            "quantity",
            "unit",
            "normalizedTonnes",
            "productionDate",
            "productProfileVersionId",
        } <= set(s)
        assert s["productProfileVersionId"] == str(profile.id)
        assert isinstance(s["quantity"], str)
        Decimal(s["quantity"])
        Decimal(s["normalizedTonnes"])

    detail = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    group = next(
        p for p in detail.product_allocations if p["productProfileVersionId"] == str(profile.id)
    )
    assert group["productionQuantitySnapshots"] == snaps

    original_qty = snaps[0]["quantity"]
    prod = seeded_db.get(CbamProductionRecord, uuid.UUID(ids[0]))
    assert prod is not None
    prod.quantity = Decimal("999")
    seeded_db.flush()
    detail2 = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    group2 = next(
        p for p in detail2.product_allocations if p["productProfileVersionId"] == str(profile.id)
    )
    assert group2["productionQuantitySnapshots"][0]["quantity"] == original_qty


def test_result_list_detail_query_count_bounded(seeded_db, engine: Engine) -> None:
    """List/detail must use bounded batch queries (not per product/month/fuel row)."""
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = seed_workbook_ready_allocation(seeded_db, user, organization)
    # Multiple production records under one profile group
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    july = next(i for i in page.items if str(i.production_date).startswith("2024-07"))
    # Bump July basis E and add second production row for same profile
    basis_page = monthly_production_basis_service.list_monthly_production_basis(
        seeded_db, user, organization.id, binding.id, page=1, page_size=20
    )
    july_basis = next(b for b in basis_page.items if b.month_start == date(2024, 7, 1))
    from ecotrace.modules.cbam.application.monthly_production_basis_service import (
        MonthlyProductionBasisUpdate,
    )

    monthly_production_basis_service.update_monthly_production_basis(
        seeded_db,
        user,
        organization.id,
        july_basis.id,
        MonthlyProductionBasisUpdate(
            row_version=july_basis.row_version,
            cbam_quantity=july.quantity + Decimal("1"),
        ),
    )
    production_record_service.create_production_record(
        seeded_db,
        user,
        organization.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=july.product_profile_version_id,
            quantity=Decimal("1"),
            unit="t",
            production_date=date(2024, 7, 16),
        ),
    )
    # Second July SC activity (same fuel — catalog only ships NATURAL_GAS; still
    # multi-source + multi-product + multi-month for query-shape evidence)
    act2 = create_ng_activity(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        qty=Decimal("10"),
        day=date(2024, 7, 18),
    )
    run_sc(seeded_db, user, organization, binding, act2, day=date(2024, 7, 18))

    executed = execute_direct_emissions_allocation(
        seeded_db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    detail0 = get_direct_emissions_allocation_result(
        seeded_db, user, organization.id, binding.id, executed.result_id
    )
    assert len(detail0.monthly_basis) == 3
    assert len(detail0.product_allocations) >= 3
    assert len(detail0.source_calculations) >= 4
    assert any(len(p["productionRecordIds"]) >= 2 for p in detail0.product_allocations)

    statements: list[str] = []

    def before_cursor(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", before_cursor)
    try:
        statements.clear()
        get_direct_emissions_allocation_result(
            seeded_db, user, organization.id, binding.id, executed.result_id
        )
        detail_statements = list(statements)
        detail_q = len(detail_statements)
        statements.clear()
        list_direct_emissions_allocation_results(
            seeded_db, user, organization.id, binding.id, page=1, page_size=20
        )
        list_q = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor)

    # Snapshot hydration is batch (one select per snapshot table family).
    def _hits(name: str) -> int:
        return sum(1 for s in detail_statements if name in s.lower())

    assert _hits("cbam_dea_monthly_basis_snapshots") <= 2
    assert _hits("cbam_dea_source_snapshots") <= 2
    assert _hits("cbam_dea_product_allocations") <= 2
    assert _hits("cbam_direct_emissions_allocation_results") <= 3
    # Total may include stale-detection lookups; soft ceiling only.
    assert detail_q <= 80, f"detail queries={detail_q}"
    assert list_q <= 80, f"list queries={list_q}"
