"""Phase 9C: product-level allocated electricity on Conventional Process responses."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import event
from tests.cbam_dea_helpers import admin, org, setup_binding
from tests.cbam_iea_helpers import (
    GOLDEN_PRODUCT_ELEC_FINALS_BY_E,
    GOLDEN_PRODUCT_EM_FINALS_BY_E,
    seed_workbook_ready_ie_allocation,
)
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.core.exceptions import NotFoundError
from ecotrace.modules.cbam.application import (
    monthly_production_basis_service,
    production_process_service,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    IndirectEmissionsAllocationExecuteRequest,
    execute_indirect_emissions_allocation,
    get_indirect_emissions_allocation_result,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    MonthlyProductionBasisUpdate,
)
from ecotrace.modules.cbam.application.production_process_constants import (
    CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY,
    CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING,
    CODE_PROCESS_PRODUCT_REQUIRED,
    READINESS_STALE,
)
from ecotrace.modules.cbam.application.production_process_service import ProductionProcessCreate


def _exec_iea(db, user, organization, binding):
    executed = execute_indirect_emissions_allocation(
        db,
        user,
        organization.id,
        binding.id,
        IndirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    return get_indirect_emissions_allocation_result(
        db, user, organization.id, binding.id, executed.result_id
    )


def _balanced_create(
    *,
    installation_id,
    profile_id,
    name: str = "P9C",
) -> ProductionProcessCreate:
    return ProductionProcessCreate(
        installation_profile_id=installation_id,
        name=name,
        product_profile_version_id=profile_id,
        produced_quantity=Decimal("10"),
        produced_quantity_unit="t",
        marketed_quantity=Decimal("10"),
        marketed_quantity_unit="t",
        non_cbam_quantity=Decimal("0"),
        non_cbam_quantity_unit="t",
        has_measurable_heat=False,
        has_waste_gas=False,
    )


def test_matching_profile_exposes_exact_allocated_mwh_and_tco2e(seeded_db) -> None:
    db = seeded_db
    user, organization, binding, installation = seed_workbook_ready_ie_allocation(db)
    detail = _exec_iea(db, user, organization, binding)
    products = {uuid.UUID(p["productProfileVersionId"]): p for p in detail.products}
    assert products
    profile_id, row = next(iter(products.items()))
    expected_mwh = Decimal(row["finalAllocatedElectricityMwh"])
    expected_em = Decimal(row["finalAllocatedIndirectEmissionsTco2e"])
    assert expected_mwh in GOLDEN_PRODUCT_ELEC_FINALS_BY_E.values()
    assert expected_em in GOLDEN_PRODUCT_EM_FINALS_BY_E.values()

    process = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        _balanced_create(installation_id=installation.id, profile_id=profile_id),
    )
    iea = process.indirect_emissions_allocation
    assert iea.current_result_id == detail.result_id
    assert iea.is_ready is True
    assert iea.is_stale is False
    assert iea.allocated_electricity_mwh == expected_mwh
    assert iea.allocated_indirect_emissions_tco2e == expected_em
    assert iea.product_allocated_value == expected_em
    assert iea.electricity_unit == "MWh"
    assert iea.result_unit == "tCO2e"
    assert iea.blocking_code is None


def test_different_profile_rows_are_not_mixed(seeded_db) -> None:
    db = seeded_db
    user, organization, binding, installation = seed_workbook_ready_ie_allocation(db)
    detail = _exec_iea(db, user, organization, binding)
    rows = list(detail.products)
    assert len(rows) >= 2
    a = rows[0]
    b = rows[1]
    pa = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        _balanced_create(
            installation_id=installation.id,
            profile_id=uuid.UUID(a["productProfileVersionId"]),
            name="A",
        ),
    )
    pb = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        _balanced_create(
            installation_id=installation.id,
            profile_id=uuid.UUID(b["productProfileVersionId"]),
            name="B",
        ),
    )
    assert pa.indirect_emissions_allocation.allocated_electricity_mwh == Decimal(
        a["finalAllocatedElectricityMwh"]
    )
    assert pb.indirect_emissions_allocation.allocated_electricity_mwh == Decimal(
        b["finalAllocatedElectricityMwh"]
    )
    assert (
        pa.indirect_emissions_allocation.allocated_electricity_mwh
        != pb.indirect_emissions_allocation.allocated_electricity_mwh
    )


def test_no_current_iea_returns_null_and_blocking(seeded_db) -> None:
    db = seeded_db
    organization = org(db)
    user = admin(db)
    binding, installation = setup_binding(db, user, organization)
    profile = create_active_ready_profile(db, user, organization.id)
    process = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        _balanced_create(installation_id=installation.id, profile_id=profile.id),
    )
    iea = process.indirect_emissions_allocation
    assert iea.current_result_id is None
    assert iea.allocated_electricity_mwh is None
    assert iea.allocated_indirect_emissions_tco2e is None
    assert iea.product_allocated_value is None
    assert CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY in process.readiness.blocking_issue_codes


def test_stale_iea_does_not_expose_product_values_as_current(seeded_db) -> None:
    db = seeded_db
    user, organization, binding, installation = seed_workbook_ready_ie_allocation(db)
    detail = _exec_iea(db, user, organization, binding)
    profile_id = uuid.UUID(detail.products[0]["productProfileVersionId"])
    process = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        _balanced_create(installation_id=installation.id, profile_id=profile_id),
    )
    assert process.indirect_emissions_allocation.allocated_electricity_mwh is not None

    # Mutate monthly basis to stale the current IEA result.
    basis = monthly_production_basis_service.list_monthly_production_basis(
        db, user, organization.id, binding.id, page=1, page_size=10
    ).items[0]
    monthly_production_basis_service.update_monthly_production_basis(
        db,
        user,
        organization.id,
        basis.id,
        MonthlyProductionBasisUpdate(
            row_version=basis.row_version,
            total_production_quantity=basis.total_production_quantity + Decimal("1"),
        ),
    )
    refreshed = production_process_service.get_production_process(
        db, user, organization.id, binding.id, process.id
    )
    iea = refreshed.indirect_emissions_allocation
    assert iea.current_result_id == detail.result_id
    assert iea.is_stale is True
    assert iea.is_ready is False
    assert iea.allocated_electricity_mwh is None
    assert iea.allocated_indirect_emissions_tco2e is None
    assert iea.product_allocated_value is None
    assert CODE_INDIRECT_EMISSIONS_ALLOCATION_NOT_READY in refreshed.readiness.blocking_issue_codes
    assert refreshed.readiness.status == READINESS_STALE


def test_missing_product_allocation_row_fails_closed(seeded_db) -> None:
    db = seeded_db
    user, organization, binding, installation = seed_workbook_ready_ie_allocation(db)
    detail = _exec_iea(db, user, organization, binding)
    other = create_active_ready_profile(
        db,
        user,
        organization.id,
        product=ensure_org_product(db, organization.id, code=f"OTHER-{uuid.uuid4().hex[:6]}"),
    )
    assert str(other.id) not in {p["productProfileVersionId"] for p in detail.products}
    process = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        _balanced_create(installation_id=installation.id, profile_id=other.id),
    )
    iea = process.indirect_emissions_allocation
    assert iea.current_result_id == detail.result_id
    assert iea.is_ready is False
    assert iea.allocated_electricity_mwh is None
    assert iea.allocated_indirect_emissions_tco2e is None
    assert iea.blocking_code == CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING
    assert (
        CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING in process.readiness.blocking_issue_codes
    )


def test_process_without_profile_does_not_guess(seeded_db) -> None:
    db = seeded_db
    user, organization, binding, installation = seed_workbook_ready_ie_allocation(db)
    detail = _exec_iea(db, user, organization, binding)
    process = production_process_service.create_production_process(
        db,
        user,
        organization.id,
        binding.id,
        ProductionProcessCreate(
            installation_profile_id=installation.id,
            name="NoProfile",
            produced_quantity=Decimal("1"),
            produced_quantity_unit="t",
            marketed_quantity=Decimal("1"),
            marketed_quantity_unit="t",
            has_measurable_heat=False,
            has_waste_gas=False,
        ),
    )
    iea = process.indirect_emissions_allocation
    assert iea.current_result_id == detail.result_id
    assert iea.allocated_electricity_mwh is None
    assert iea.allocated_indirect_emissions_tco2e is None
    assert iea.product_allocated_value is None
    assert CODE_PROCESS_PRODUCT_REQUIRED in process.readiness.blocking_issue_codes
    assert (
        CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING
        not in process.readiness.blocking_issue_codes
    )


def test_cross_org_iea_product_rows_are_not_resolved(seeded_db) -> None:
    db = seeded_db
    user_a, org_a, binding_a, installation_a = seed_workbook_ready_ie_allocation(db)
    detail_a = _exec_iea(db, user_a, org_a, binding_a)
    profile_a = uuid.UUID(detail_a.products[0]["productProfileVersionId"])
    mwh_a = Decimal(detail_a.products[0]["finalAllocatedElectricityMwh"])

    user_b, org_b, binding_b, installation_b = seed_workbook_ready_ie_allocation(db)
    _exec_iea(db, user_b, org_b, binding_b)

    process_b = production_process_service.create_production_process(
        db,
        user_b,
        org_b.id,
        binding_b.id,
        _balanced_create(
            installation_id=installation_b.id,
            profile_id=create_active_ready_profile(
                db,
                user_b,
                org_b.id,
                product=ensure_org_product(db, org_b.id, code=f"BONLY-{uuid.uuid4().hex[:6]}"),
            ).id,
            name="OrgB",
        ),
    )
    assert process_b.indirect_emissions_allocation.allocated_electricity_mwh is None
    assert (
        process_b.indirect_emissions_allocation.blocking_code
        == CODE_INDIRECT_EMISSIONS_PRODUCT_ALLOCATION_MISSING
    )

    process_a = production_process_service.create_production_process(
        db,
        user_a,
        org_a.id,
        binding_a.id,
        _balanced_create(
            installation_id=installation_a.id,
            profile_id=profile_a,
            name="OrgA",
        ),
    )
    assert process_a.indirect_emissions_allocation.allocated_electricity_mwh == mwh_a

    # Org B cannot read org A process.
    with pytest.raises(NotFoundError):
        production_process_service.get_production_process(
            db, user_b, org_b.id, binding_b.id, process_a.id
        )


def test_process_list_does_not_n_plus_one_iea_product_queries(seeded_db) -> None:
    db = seeded_db
    user, organization, binding, installation = seed_workbook_ready_ie_allocation(db)
    detail = _exec_iea(db, user, organization, binding)
    for i, row in enumerate(detail.products):
        production_process_service.create_production_process(
            db,
            user,
            organization.id,
            binding.id,
            _balanced_create(
                installation_id=installation.id,
                profile_id=uuid.UUID(row["productProfileVersionId"]),
                name=f"L{i}",
            ),
        )

    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(str(statement))

    event.listen(db.bind, "before_cursor_execute", before_cursor_execute)
    try:
        page = production_process_service.list_production_processes(
            db, user, organization.id, binding.id, page=1, page_size=50
        )
    finally:
        event.remove(db.bind, "before_cursor_execute", before_cursor_execute)

    assert len(page.items) == len(detail.products)
    iea_product_selects = [
        s
        for s in statements
        if "cbam_iea_product_allocations" in s.lower() and s.lstrip().upper().startswith("SELECT")
    ]
    # One bounded select via IEA summary/detail — must not scale with process count.
    assert len(iea_product_selects) <= 2
    assert len(iea_product_selects) < len(page.items)
    for item in page.items:
        assert item.indirect_emissions_allocation.allocated_electricity_mwh is not None
