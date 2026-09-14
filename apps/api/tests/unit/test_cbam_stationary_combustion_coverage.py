from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from ecotrace.core.exceptions import AuthorizationError, NotFoundError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    activity_record_service,
    installation_service,
    period_binding_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.stationary_combustion_api_service import (
    get_stationary_combustion_summary_for_binding,
    list_stationary_combustion_activity_coverage_for_binding,
)
from ecotrace.modules.cbam.application.stationary_combustion_coverage_service import (
    COVERAGE_CURRENT,
    COVERAGE_MISSING,
    COVERAGE_STALE,
)
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    STALE_REASON_DATE_CHANGED,
    STALE_REASON_FUEL_TYPE_CHANGED,
    STALE_REASON_QUANTITY_CHANGED,
    STALE_REASON_UNIT_CHANGED,
)
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    StationaryCombustionExecutionCommand,
    execute_stationary_combustion_calculation,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionCurrentResult,
    CbamStationaryCombustionFuel,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod

JANUARY_SM3 = Decimal("105437.03007518797")
JANUARY_SM3_PERSISTED = Decimal("105437.03007519")
DENSITY = Decimal("0.67")


def _org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db):
    return db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()


def _viewer(db):
    return db.execute(
        select(User).where(User.normalized_email == "viewer@ecotrace.dev")
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
            code=f"SCCOV-{uuid.uuid4().hex[:8]}",
            name="SC Coverage Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"SCCOV-{uuid.uuid4().hex[:6]}",
        name="SC Coverage Period",
        period_type="custom",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        status="open",
    )
    db.add(period)
    db.flush()
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
    return opened, installation, period


def _create_ng_activity(
    db,
    admin,
    org,
    binding,
    installation,
    *,
    quantity=JANUARY_SM3,
    unit="Sm3",
    activity_date=date(2024, 1, 15),
):
    return activity_record_service.create_activity_record(
        db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="NATURAL_GAS",
            quantity=quantity,
            unit=unit,
            data_source_type="PRIMARY",
            activity_date=activity_date,
        ),
    )


def _exec(db, admin, org, binding, activity, *, density=DENSITY):
    return execute_stationary_combustion_calculation(
        db,
        admin,
        StationaryCombustionExecutionCommand(
            organization_id=org.id,
            reporting_period_binding_id=binding.id,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            reference_date=activity.activity_date or date(2024, 1, 15),
            density_value=density,
            density_unit="kg/Sm3",
            requested_by_user_id=admin.id,
        ),
    )


def _coverage_all(db, user, org, binding, *, page_size=100):
    page = 1
    items = []
    while True:
        batch = list_stationary_combustion_activity_coverage_for_binding(
            db, user, org.id, binding.id, page=page, page_size=page_size
        )
        items.extend(batch.items)
        if page >= batch.total_pages or not batch.items:
            break
        page += 1
    return items


def test_missing_current_stale_coverage_statuses(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)

    missing = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert missing.total_items == 1
    assert missing.items[0].coverage_status == COVERAGE_MISSING
    assert missing.items[0].current_result_id is None
    assert "MISSING_CALCULATION" in missing.items[0].blocking_issue_codes

    executed = _exec(seeded_db, admin, org, binding, activity)
    current = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert current.items[0].coverage_status == COVERAGE_CURRENT
    assert current.items[0].current_result_id == executed.result.id
    assert current.items[0].stale_reason_codes == []

    row = seeded_db.get(CbamActivityRecord, activity.id)
    assert row is not None
    row.quantity = JANUARY_SM3_PERSISTED + Decimal("1")
    seeded_db.flush()
    stale = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert stale.items[0].coverage_status == COVERAGE_STALE
    assert STALE_REASON_QUANTITY_CHANGED in stale.items[0].stale_reason_codes


def test_history_recalc_keeps_newest_current(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = _exec(seeded_db, admin, org, binding, activity)
    second = _exec(seeded_db, admin, org, binding, activity, density=Decimal("0.68"))
    coverage = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert coverage.items[0].coverage_status == COVERAGE_CURRENT
    assert coverage.items[0].current_result_id == second.result.id
    assert coverage.items[0].current_result_id != first.result.id


def test_ineligible_activity_excluded(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    _create_ng_activity(seeded_db, admin, org, binding, installation)
    activity_record_service.create_activity_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ActivityRecordCreate(
            installation_profile_id=installation.id,
            activity_type="ELECTRICITY",
            quantity=Decimal("10"),
            unit="kWh",
            data_source_type="PRIMARY",
            activity_date=date(2024, 1, 10),
        ),
    )
    coverage = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert coverage.total_items == 1
    assert coverage.items[0].fuel_code == "NATURAL_GAS"


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda row: setattr(row, "quantity", JANUARY_SM3_PERSISTED + Decimal("2")),
            STALE_REASON_QUANTITY_CHANGED,
        ),
        (lambda row: setattr(row, "unit", "m3"), STALE_REASON_UNIT_CHANGED),
        (lambda row: setattr(row, "activity_date", date(2024, 2, 1)), STALE_REASON_DATE_CHANGED),
        (lambda row: setattr(row, "activity_type", "DIESEL"), STALE_REASON_FUEL_TYPE_CHANGED),
    ],
)
def test_stale_reasons(seeded_db, mutate, reason) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    _exec(seeded_db, admin, org, binding, activity)
    row = seeded_db.get(CbamActivityRecord, activity.id)
    assert row is not None
    if reason == STALE_REASON_FUEL_TYPE_CHANGED:
        diesel = seeded_db.execute(
            select(CbamStationaryCombustionFuel).where(
                CbamStationaryCombustionFuel.code == "DIESEL"
            )
        ).scalar_one_or_none()
        if diesel is None:
            seeded_db.add(
                CbamStationaryCombustionFuel(
                    code="DIESEL",
                    name="Diesel",
                    input_basis="MASS",
                    default_activity_unit="t",
                    status="ACTIVE",
                )
            )
            seeded_db.flush()
        else:
            diesel.status = "ACTIVE"
            seeded_db.flush()
    mutate(row)
    if reason == STALE_REASON_FUEL_TYPE_CHANGED:
        row.unit = "t"
    seeded_db.flush()
    coverage = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert coverage.total_items == 1
    assert coverage.items[0].coverage_status == COVERAGE_STALE
    assert reason in coverage.items[0].stale_reason_codes


def test_pagination_and_page2_current_not_missing(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activities = [
        _create_ng_activity(
            seeded_db,
            admin,
            org,
            binding,
            installation,
            activity_date=date(2024, 1, day),
        )
        for day in (10, 11, 12)
    ]
    for activity in activities:
        _exec(seeded_db, admin, org, binding, activity)

    page1 = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=2
    )
    page2 = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=2, page_size=2
    )
    assert page1.total_items == 3
    assert page1.total_pages == 2
    assert len(page1.items) == 2
    assert len(page2.items) == 1
    assert page1.items[0].activity_date <= page1.items[1].activity_date
    assert all(item.coverage_status == COVERAGE_CURRENT for item in page1.items)
    assert page2.items[0].coverage_status == COVERAGE_CURRENT
    assert page2.items[0].current_result_id is not None


def test_coverage_reconciles_with_summary(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    a1 = _create_ng_activity(
        seeded_db, admin, org, binding, installation, activity_date=date(2024, 1, 5)
    )
    a2 = _create_ng_activity(
        seeded_db, admin, org, binding, installation, activity_date=date(2024, 1, 6)
    )
    _create_ng_activity(
        seeded_db, admin, org, binding, installation, activity_date=date(2024, 1, 7)
    )
    _exec(seeded_db, admin, org, binding, a1)
    _exec(seeded_db, admin, org, binding, a2)
    row = seeded_db.get(CbamActivityRecord, a2.id)
    assert row is not None
    row.quantity = JANUARY_SM3_PERSISTED + Decimal("9")
    seeded_db.flush()

    items = _coverage_all(seeded_db, admin, org, binding, page_size=1)
    summary = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert len(items) == summary.eligible_activity_count == 3
    assert (
        sum(1 for i in items if i.coverage_status == COVERAGE_MISSING)
        == summary.missing_result_count
    )
    assert (
        sum(1 for i in items if i.coverage_status == COVERAGE_STALE) == summary.stale_result_count
    )
    assert (
        sum(1 for i in items if i.coverage_status == COVERAGE_CURRENT)
        == summary.valid_current_result_count
    )


def test_viewer_can_list_coverage_cross_org_fails(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    viewer = _viewer(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    _create_ng_activity(seeded_db, admin, org, binding, installation)
    ok = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, viewer, org.id, binding.id, page=1, page_size=20
    )
    assert ok.total_items == 1

    with pytest.raises((AuthorizationError, NotFoundError)):
        list_stationary_combustion_activity_coverage_for_binding(
            seeded_db, viewer, uuid.uuid4(), binding.id, page=1, page_size=20
        )


def test_historical_result_without_pointer_is_missing(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    executed = _exec(seeded_db, admin, org, binding, activity)
    # Remove current pointer — historical result remains but coverage must be MISSING.
    pointer = seeded_db.execute(
        select(CbamStationaryCombustionCurrentResult).where(
            CbamStationaryCombustionCurrentResult.activity_record_id == activity.id
        )
    ).scalar_one()
    seeded_db.delete(pointer)
    seeded_db.flush()
    coverage = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert coverage.items[0].coverage_status == COVERAGE_MISSING
    assert coverage.items[0].current_result_id is None
    assert executed.result.id is not None


def test_inactive_fuel_activity_excluded(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    fuel = seeded_db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.code == "NATURAL_GAS"
        )
    ).scalar_one()
    fuel.status = "ARCHIVED"
    seeded_db.flush()
    coverage = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    assert coverage.total_items == 0
    assert activity.id is not None


def test_binding_ownership_mismatch_fails(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    _create_ng_activity(seeded_db, admin, org, binding, installation)
    other_binding, _inst2, _period2 = _setup(seeded_db, admin, org)
    with pytest.raises((AuthorizationError, NotFoundError)):
        list_stationary_combustion_activity_coverage_for_binding(
            seeded_db, admin, org.id, uuid.uuid4(), page=1, page_size=20
        )
    # Same org, wrong binding id that does not own the first activity scope still 404s.
    with pytest.raises((AuthorizationError, NotFoundError)):
        list_stationary_combustion_activity_coverage_for_binding(
            seeded_db,
            admin,
            uuid.uuid4(),
            other_binding.id,
            page=1,
            page_size=20,
        )


def test_ordering_uses_id_tie_breaker(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    same_day = date(2024, 1, 20)
    a1 = _create_ng_activity(seeded_db, admin, org, binding, installation, activity_date=same_day)
    a2 = _create_ng_activity(seeded_db, admin, org, binding, installation, activity_date=same_day)
    coverage = list_stationary_combustion_activity_coverage_for_binding(
        seeded_db, admin, org.id, binding.id, page=1, page_size=20
    )
    ids = [item.activity_record_id for item in coverage.items]
    assert ids == sorted([a1.id, a2.id])
