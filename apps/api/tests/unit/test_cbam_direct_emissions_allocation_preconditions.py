"""Phase 7A-2+ independent readiness/execution precondition tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests.cbam_dea_helpers import (
    admin,
    create_ng_activity,
    org,
    run_sc,
    seed_workbook_ready_allocation,
    setup_binding,
)

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError
from ecotrace.modules.cbam.application import (
    production_record_service,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
    execute_direct_emissions_allocation,
    get_direct_emissions_allocation_readiness,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamDirectEmissionsAllocationCurrent,
    CbamDirectEmissionsAllocationResult,
    CbamProductionRecord,
    CbamProductProfileVersion,
)
from ecotrace.modules.organizations.infrastructure.models import Organization


def _count_results(db: Session, binding_id: uuid.UUID) -> int:
    return (
        db.execute(
            select(CbamDirectEmissionsAllocationResult).where(
                CbamDirectEmissionsAllocationResult.reporting_period_binding_id == binding_id
            )
        )
        .scalars()
        .all()
        .__len__()
    )


def _pointer(db: Session, binding_id: uuid.UUID):
    return db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding_id
        )
    ).scalar_one_or_none()


def _assert_fail_closed(
    db: Session,
    user,
    organization,
    binding,
    *,
    expected_code: str,
    client_id: uuid.UUID | None = None,
) -> None:
    before_n = _count_results(db, binding.id)
    before_ptr = _pointer(db, binding.id)
    before_ptr_id = before_ptr.current_result_id if before_ptr else None
    cid = client_id or uuid.uuid4()
    with pytest.raises(BusinessRuleError) as exc:
        execute_direct_emissions_allocation(
            db,
            user,
            organization.id,
            binding.id,
            DirectEmissionsAllocationExecuteRequest(client_request_id=cid),
        )
    codes = [d.get("code") for d in (exc.value.details or [])]
    assert expected_code in codes, codes
    assert "IntegrityError" not in str(exc.value)
    assert "sqlalchemy" not in str(exc.value).lower()
    assert _count_results(db, binding.id) == before_n
    after_ptr = _pointer(db, binding.id)
    after_id = after_ptr.current_result_id if after_ptr else None
    assert after_id == before_ptr_id
    reserved = db.execute(
        select(CbamDirectEmissionsAllocationResult).where(
            CbamDirectEmissionsAllocationResult.client_request_id == cid
        )
    ).scalar_one_or_none()
    assert reserved is None


def test_precondition_stale_stationary_combustion_source(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    # Materially change activity after SC → SC result stale for current use
    act = seeded_db.execute(
        select(CbamActivityRecord)
        .where(
            CbamActivityRecord.reporting_period_binding_id == binding.id,
            CbamActivityRecord.status == "active",
        )
        .limit(1)
    ).scalar_one()
    act.quantity = act.quantity + Decimal("10")
    seeded_db.flush()
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "DIRECT_EMISSIONS_STALE" in readiness.blocking_issue_codes
    assert readiness.allocation_ready is False
    _assert_fail_closed(
        seeded_db, user, organization, binding, expected_code="DIRECT_EMISSIONS_STALE"
    )


def test_precondition_production_reconciliation_unavailable(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    for item in page.items:
        row = seeded_db.get(CbamProductionRecord, item.id)
        assert row is not None
        row.production_date = None
    seeded_db.flush()
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "PRODUCTION_RECONCILIATION_UNAVAILABLE" in readiness.blocking_issue_codes
    _assert_fail_closed(
        seeded_db,
        user,
        organization,
        binding,
        expected_code="PRODUCTION_RECONCILIATION_UNAVAILABLE",
    )


def test_precondition_invalid_production_profile_link(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None and row.product_profile_version_id is not None
    profile = seeded_db.get(CbamProductProfileVersion, row.product_profile_version_id)
    assert profile is not None
    profile.classification_ready = False
    seeded_db.flush()
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "PRODUCTION_PROFILE_LINK_INVALID" in readiness.blocking_issue_codes
    _assert_fail_closed(
        seeded_db,
        user,
        organization,
        binding,
        expected_code="PRODUCTION_PROFILE_LINK_INVALID",
    )


def test_precondition_missing_production_profile_link(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    for item in page.items:
        row = seeded_db.get(CbamProductionRecord, item.id)
        assert row is not None
        row.product_profile_version_id = None
    seeded_db.flush()
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "PRODUCTION_PROFILE_LINK_MISSING" in readiness.blocking_issue_codes
    _assert_fail_closed(
        seeded_db,
        user,
        organization,
        binding,
        expected_code="PRODUCTION_PROFILE_LINK_MISSING",
    )


def test_precondition_zero_allocation_denominator(seeded_db, monkeypatch) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    import ecotrace.modules.cbam.application.direct_emissions_allocation_service as svc

    real = svc._resolve_context

    def forced(db, u, oid, bid):
        ctx = real(db, u, oid, bid)
        for g in ctx["groups"].values():
            g["qty"] = Decimal("0")
        ctx["denom"] = Decimal("0")
        if "ZERO_ALLOCATION_DENOMINATOR" not in ctx["blocking"]:
            ctx["blocking"].append("ZERO_ALLOCATION_DENOMINATOR")
        return ctx

    monkeypatch.setattr(svc, "_resolve_context", forced)
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "ZERO_ALLOCATION_DENOMINATOR" in readiness.blocking_issue_codes
    _assert_fail_closed(
        seeded_db,
        user,
        organization,
        binding,
        expected_code="ZERO_ALLOCATION_DENOMINATOR",
    )


def test_precondition_incompatible_production_mass_unit(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    page = production_record_service.list_production_records(
        seeded_db, user, organization.id, binding.id, page=1, page_size=50
    )
    row = seeded_db.get(CbamProductionRecord, page.items[0].id)
    assert row is not None
    row.unit = "kWh"
    seeded_db.flush()
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "INCOMPATIBLE_PRODUCTION_UNIT" in readiness.blocking_issue_codes
    _assert_fail_closed(
        seeded_db,
        user,
        organization,
        binding,
        expected_code="INCOMPATIBLE_PRODUCTION_UNIT",
    )


def test_precondition_combustion_month_outside_period(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, installation = setup_binding(
        seeded_db, user, organization, start=date(2024, 7, 1), end=date(2024, 9, 30)
    )
    # Activity date outside period → month not covered
    act = create_ng_activity(
        seeded_db,
        user,
        organization,
        binding,
        installation,
        qty=Decimal("188"),
        day=date(2024, 1, 15),
    )
    run_sc(seeded_db, user, organization, binding, act, day=date(2024, 1, 15))
    readiness = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, binding.id
    )
    assert "COMBUSTION_MONTH_NOT_COVERED" in readiness.blocking_issue_codes
    _assert_fail_closed(
        seeded_db,
        user,
        organization,
        binding,
        expected_code="COMBUSTION_MONTH_NOT_COVERED",
    )


def test_precondition_cross_organization_readiness(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    other = Organization(
        id=uuid.uuid4(),
        name="DEA Isolation Org",
        slug=f"dea-iso-{uuid.uuid4().hex[:6]}",
        country_code="US",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(other)
    seeded_db.flush()
    with pytest.raises(NotFoundError):
        get_direct_emissions_allocation_readiness(seeded_db, user, other.id, binding.id)


def test_precondition_cross_binding_readiness(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    _binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    other_binding, _ = setup_binding(
        seeded_db, user, organization, start=date(2025, 1, 1), end=date(2025, 3, 31)
    )
    with pytest.raises(NotFoundError):
        get_direct_emissions_allocation_readiness(seeded_db, user, organization.id, uuid.uuid4())
    # Wrong binding id that exists but wrong for execute of first binding's data
    r = get_direct_emissions_allocation_readiness(
        seeded_db, user, organization.id, other_binding.id
    )
    assert r.allocation_ready is False


def test_precondition_cross_organization_execution(seeded_db) -> None:
    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    other = Organization(
        id=uuid.uuid4(),
        name="DEA Exec Iso",
        slug=f"dea-ex-{uuid.uuid4().hex[:6]}",
        country_code="US",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(other)
    seeded_db.flush()
    with pytest.raises(NotFoundError):
        execute_direct_emissions_allocation(
            seeded_db,
            user,
            other.id,
            binding.id,
            DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
        )
    assert _count_results(seeded_db, binding.id) == 0


def test_precondition_cross_binding_result_access(seeded_db) -> None:
    from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
        get_direct_emissions_allocation_result,
    )

    organization = org(seeded_db)
    user = admin(seeded_db)
    binding, _ = seed_workbook_ready_allocation(seeded_db, user, organization)
    executed = execute_direct_emissions_allocation(
        seeded_db,
        user,
        organization.id,
        binding.id,
        DirectEmissionsAllocationExecuteRequest(client_request_id=uuid.uuid4()),
    )
    other_binding, _ = setup_binding(
        seeded_db, user, organization, start=date(2025, 4, 1), end=date(2025, 6, 30)
    )
    with pytest.raises(NotFoundError):
        get_direct_emissions_allocation_result(
            seeded_db,
            user,
            organization.id,
            other_binding.id,
            executed.result_id,
        )
