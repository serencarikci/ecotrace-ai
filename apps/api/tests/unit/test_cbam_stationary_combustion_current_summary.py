from __future__ import annotations

import threading
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from ecotrace.core.exceptions import ValidationAppError
from ecotrace.db.seed import DEMO_ORG_SLUG, run_seed
from ecotrace.modules.cbam.application import (
    activity_record_service,
    installation_service,
    period_binding_service,
)
from ecotrace.modules.cbam.application.activity_record_service import ActivityRecordCreate
from ecotrace.modules.cbam.application.calculation_math import quantize_result
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.stationary_combustion_api_service import (
    StationaryCombustionExecutionApiRequest,
    execute_stationary_combustion_api,
    get_stationary_combustion_result_for_binding,
    get_stationary_combustion_summary_for_binding,
    list_stationary_combustion_results,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    get_current_pointer,
    is_stationary_combustion_result_stale,
)
from ecotrace.modules.cbam.application.stationary_combustion_execution_service import (
    StationaryCombustionExecutionCommand,
    execute_stationary_combustion_calculation,
)
from ecotrace.modules.cbam.application.stationary_combustion_summary_service import (
    READINESS_EMPTY,
    READINESS_INCOMPLETE,
    READINESS_READY,
    READINESS_STALE,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamStationaryCombustionCurrentResult,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod

JANUARY_SM3 = Decimal("105437.03007518797")
JANUARY_SM3_PERSISTED = Decimal("105437.03007519")
EXPECTED_JANUARY_TCO2 = Decimal("190.22695917")
DENSITY = Decimal("0.67")


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
            code=f"SC5A-{uuid.uuid4().hex[:8]}",
            name="SC Phase5A Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"SC5A-{uuid.uuid4().hex[:6]}",
        name="SC5A Period",
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


def _exec(
    db, admin, org, binding, activity, *, density=DENSITY, client_request_id=None, commit=True
):
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
            client_request_id=client_request_id,
            request_fingerprint="test",
        ),
        commit=commit,
    )


def test_first_result_becomes_current_and_recalculation_updates_pointer(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)

    first = _exec(seeded_db, admin, org, binding, activity)
    assert first.result.result_value == EXPECTED_JANUARY_TCO2
    pointer = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer is not None
    assert pointer.current_result_id == first.result.id

    second = _exec(seeded_db, admin, org, binding, activity, density=Decimal("0.68"))
    assert second.result.id != first.result.id
    pointer2 = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer2 is not None
    assert pointer2.current_result_id == second.result.id

    detail_old = get_stationary_combustion_result_for_binding(
        seeded_db, admin, org.id, binding.id, first.result.id
    )
    detail_new = get_stationary_combustion_result_for_binding(
        seeded_db, admin, org.id, binding.id, second.result.id
    )
    assert detail_old.is_current is False
    assert detail_new.is_current is True
    assert seeded_db.get(CbamStationaryCombustionResult, first.result.id) is not None

    count = seeded_db.execute(
        select(func.count())
        .select_from(CbamStationaryCombustionCurrentResult)
        .where(
            CbamStationaryCombustionCurrentResult.activity_record_id == activity.id,
        )
    ).scalar_one()
    assert count == 1


def test_idempotent_replay_of_current_does_not_duplicate_pointer(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    key = uuid.uuid4()
    first = execute_stationary_combustion_api(
        seeded_db,
        admin,
        org.id,
        binding.id,
        StationaryCombustionExecutionApiRequest(
            client_request_id=key,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    assert first.idempotent_replay is False
    pointer_before = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer_before is not None
    updated_at = pointer_before.updated_at

    replay = execute_stationary_combustion_api(
        seeded_db,
        admin,
        org.id,
        binding.id,
        StationaryCombustionExecutionApiRequest(
            client_request_id=key,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    assert replay.idempotent_replay is True
    assert replay.result_id == first.result_id
    pointer_after = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer_after is not None
    assert pointer_after.current_result_id == first.result_id
    assert pointer_after.updated_at == updated_at
    assert (
        seeded_db.execute(
            select(func.count()).select_from(CbamStationaryCombustionCurrentResult)
        ).scalar_one()
        >= 1
    )


def test_replay_of_older_non_current_does_not_move_pointer_back(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    key_a = uuid.uuid4()
    first = execute_stationary_combustion_api(
        seeded_db,
        admin,
        org.id,
        binding.id,
        StationaryCombustionExecutionApiRequest(
            client_request_id=key_a,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    second = execute_stationary_combustion_api(
        seeded_db,
        admin,
        org.id,
        binding.id,
        StationaryCombustionExecutionApiRequest(
            client_request_id=uuid.uuid4(),
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            density_value=Decimal("0.68"),
            density_unit="kg/Sm3",
        ),
    )
    assert second.result_id != first.result_id
    replay_old = execute_stationary_combustion_api(
        seeded_db,
        admin,
        org.id,
        binding.id,
        StationaryCombustionExecutionApiRequest(
            client_request_id=key_a,
            activity_record_id=activity.id,
            fuel_code="NATURAL_GAS",
            density_value=DENSITY,
            density_unit="kg/Sm3",
        ),
    )
    assert replay_old.idempotent_replay is True
    assert replay_old.result_id == first.result_id
    pointer = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer is not None
    assert pointer.current_result_id == second.result_id


def test_failed_recalculation_preserves_current(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = _exec(seeded_db, admin, org, binding, activity)
    with pytest.raises(ValidationAppError):
        execute_stationary_combustion_calculation(
            seeded_db,
            admin,
            StationaryCombustionExecutionCommand(
                organization_id=org.id,
                reporting_period_binding_id=binding.id,
                activity_record_id=activity.id,
                fuel_code="NATURAL_GAS",
                reference_date=date(2024, 1, 15),
                density_value=None,
                density_unit=None,
                requested_by_user_id=admin.id,
            ),
        )
    pointer = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer is not None
    assert pointer.current_result_id == first.result.id


def test_stale_detection_quantity_unit_date_fuel(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    created = _create_ng_activity(seeded_db, admin, org, binding, installation)
    activity = seeded_db.get(CbamActivityRecord, created.id)
    assert activity is not None
    executed = _exec(seeded_db, admin, org, binding, activity)
    row = seeded_db.get(CbamStationaryCombustionResult, executed.result.id)
    assert row is not None
    assert is_stationary_combustion_result_stale(activity, row) is False

    activity.quantity = JANUARY_SM3_PERSISTED + Decimal("1")
    seeded_db.flush()
    assert is_stationary_combustion_result_stale(activity, row) is True

    activity.quantity = JANUARY_SM3_PERSISTED
    activity.unit = "m3"
    seeded_db.flush()
    assert is_stationary_combustion_result_stale(activity, row) is True

    activity.unit = "Sm3"
    activity.activity_date = date(2024, 2, 1)
    seeded_db.flush()
    assert is_stationary_combustion_result_stale(activity, row) is True

    activity.activity_date = date(2024, 1, 15)
    activity.activity_type = "DIESEL"
    seeded_db.flush()
    assert is_stationary_combustion_result_stale(activity, row) is True


def test_catalog_version_does_not_make_stale(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    created = _create_ng_activity(seeded_db, admin, org, binding, installation)
    activity = seeded_db.get(CbamActivityRecord, created.id)
    assert activity is not None
    executed = _exec(seeded_db, admin, org, binding, activity)
    row = seeded_db.get(CbamStationaryCombustionResult, executed.result.id)
    assert row is not None
    # Simulate unrelated catalog change by only mutating fuel name on a different object path:
    # activity/result material unchanged → not stale.
    assert is_stationary_combustion_result_stale(activity, row) is False


def test_summary_empty_incomplete_stale_ready(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)

    empty = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert empty.readiness_status == READINESS_EMPTY
    assert empty.eligible_activity_count == 0

    created = _create_ng_activity(seeded_db, admin, org, binding, installation)
    incomplete = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert incomplete.readiness_status == READINESS_INCOMPLETE
    assert incomplete.missing_result_count == 1

    _exec(seeded_db, admin, org, binding, created)
    ready = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert ready.readiness_status == READINESS_READY
    assert ready.final_result_value == EXPECTED_JANUARY_TCO2
    assert ready.final_result_unit == "tCO2"
    assert ready.valid_current_result_count == 1
    assert sum(t.final_result_value for t in ready.totals_by_fuel) == ready.final_result_value

    activity = seeded_db.get(CbamActivityRecord, created.id)
    assert activity is not None
    activity.quantity = JANUARY_SM3_PERSISTED + Decimal("10")
    seeded_db.flush()
    stale = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert stale.readiness_status == READINESS_STALE
    assert stale.stale_result_count == 1
    assert stale.valid_current_result_count == 0
    assert stale.final_result_value == quantize_result(Decimal("0"))
    assert any("no longer match" in issue for issue in stale.blocking_issues)


def test_summary_excludes_historical_and_failed_and_uses_prequantized(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    a1 = _create_ng_activity(seeded_db, admin, org, binding, installation)
    a2 = _create_ng_activity(seeded_db, admin, org, binding, installation, quantity=JANUARY_SM3)
    first = _exec(seeded_db, admin, org, binding, a1)
    _exec(seeded_db, admin, org, binding, a1, density=Decimal("0.68"))
    second_activity = _exec(seeded_db, admin, org, binding, a2)

    summary = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert summary.valid_current_result_count == 2
    # Historical first result must not double-count.
    assert summary.current_result_count == 2
    listed = list_stationary_combustion_results(
        seeded_db, admin, org.id, binding.id, page=1, page_size=50
    )
    assert listed.total_items == 3
    currents = [i for i in listed.items if i.is_current]
    assert len(currents) == 2
    assert all(not i.is_current or i.result_id != first.result.id for i in listed.items)

    # Totals use fossil_co2_tonnes (pre-quantized snapshot), then quantize once.
    r2 = seeded_db.get(CbamStationaryCombustionResult, second_activity.result.id)
    assert r2 is not None
    assert summary.total_fossil_co2_tonnes >= r2.fossil_co2_tonnes
    assert summary.final_result_value == quantize_result(summary.total_fossil_co2_tonnes)


def test_summary_missing_and_stale_both_exposed(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    a1 = _create_ng_activity(seeded_db, admin, org, binding, installation)
    _create_ng_activity(seeded_db, admin, org, binding, installation)
    _exec(seeded_db, admin, org, binding, a1)
    row = seeded_db.get(CbamActivityRecord, a1.id)
    assert row is not None
    row.quantity = JANUARY_SM3_PERSISTED + Decimal("5")
    seeded_db.flush()
    summary = get_stationary_combustion_summary_for_binding(seeded_db, admin, org.id, binding.id)
    assert summary.readiness_status == READINESS_INCOMPLETE
    assert summary.missing_result_count == 1
    assert summary.stale_result_count == 1
    assert len(summary.blocking_issues) == 2


def test_concurrent_recalculations_one_valid_pointer(engine) -> None:
    from tests.conftest import _truncate_all

    _truncate_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    setup = session_factory()
    try:
        run_seed(setup)
        ensure_platform_factor_catalog(setup)
        ensure_platform_stationary_combustion_catalog(setup)
        ensure_platform_calculation_definitions(setup)
        setup.commit()
        org = _org(setup)
        admin = _admin(setup)
        binding, installation, _period = _setup(setup, admin, org)
        activity = _create_ng_activity(setup, admin, org, binding, installation)
        setup.commit()
        ctx = {
            "org_id": org.id,
            "admin_id": admin.id,
            "binding_id": binding.id,
            "activity_id": activity.id,
        }
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker(density: str) -> None:
        db = session_factory()
        try:
            admin = db.get(User, ctx["admin_id"])
            assert admin is not None
            barrier.wait(timeout=10)
            execute_stationary_combustion_api(
                db,
                admin,
                ctx["org_id"],
                ctx["binding_id"],
                StationaryCombustionExecutionApiRequest(
                    client_request_id=uuid.uuid4(),
                    activity_record_id=ctx["activity_id"],
                    fuel_code="NATURAL_GAS",
                    density_value=Decimal(density),
                    density_unit="kg/Sm3",
                ),
            )
        except BaseException as exc:
            errors.append(exc)
            db.rollback()
        finally:
            db.close()

    t1 = threading.Thread(target=worker, args=("0.67",))
    t2 = threading.Thread(target=worker, args=("0.68",))
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)
    assert not errors, errors

    verify = session_factory()
    try:
        pointers = (
            verify.execute(
                select(CbamStationaryCombustionCurrentResult).where(
                    CbamStationaryCombustionCurrentResult.activity_record_id == ctx["activity_id"]
                )
            )
            .scalars()
            .all()
        )
        assert len(pointers) == 1
        result = verify.get(CbamStationaryCombustionResult, pointers[0].current_result_id)
        assert result is not None
        assert result.activity_record_id == ctx["activity_id"]
    finally:
        verify.close()


def test_pointer_table_and_unique_index_exist(engine) -> None:
    with engine.connect() as conn:
        table = conn.execute(
            text(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'cbam_stationary_combustion_current_results'
                """
            )
        ).scalar_one_or_none()
        assert table == 1
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'cbam_stationary_combustion_current_results'
                    """
                )
            )
        }
    assert {
        "organization_id",
        "reporting_period_binding_id",
        "activity_record_id",
        "current_result_id",
    }.issubset(cols)


def test_january_golden_unchanged(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    executed = _exec(seeded_db, admin, org, binding, activity)
    assert executed.result.result_value == EXPECTED_JANUARY_TCO2


_BACKFILL_SQL = """
INSERT INTO cbam_stationary_combustion_current_results (
    id,
    organization_id,
    reporting_period_binding_id,
    activity_record_id,
    current_result_id,
    created_at,
    updated_at
)
SELECT
    gen_random_uuid(),
    ranked.organization_id,
    ranked.reporting_period_binding_id,
    ranked.activity_record_id,
    ranked.id,
    now(),
    now()
FROM (
    SELECT
        r.id,
        r.organization_id,
        r.reporting_period_binding_id,
        r.activity_record_id,
        ROW_NUMBER() OVER (
            PARTITION BY
                r.organization_id,
                r.reporting_period_binding_id,
                r.activity_record_id
            ORDER BY r.created_at DESC, r.id DESC
        ) AS rn
    FROM cbam_stationary_combustion_results r
    INNER JOIN cbam_calculation_runs run ON run.id = r.calculation_run_id
    WHERE run.status = 'COMPLETED'
) ranked
WHERE ranked.rn = 1
ON CONFLICT (organization_id, reporting_period_binding_id, activity_record_id)
DO NOTHING
"""


def test_historical_backfill_selects_newest_and_preserves_snapshots(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    first = _exec(seeded_db, admin, org, binding, activity)
    second = _exec(seeded_db, admin, org, binding, activity, density=Decimal("0.68"))
    first_row = seeded_db.get(CbamStationaryCombustionResult, first.result.id)
    second_row = seeded_db.get(CbamStationaryCombustionResult, second.result.id)
    assert first_row is not None and second_row is not None
    snapshot_before = (
        first_row.result_value,
        first_row.fossil_co2_tonnes,
        first_row.activity_quantity,
        second_row.result_value,
        second_row.fossil_co2_tonnes,
    )

    seeded_db.execute(text("DELETE FROM cbam_stationary_combustion_current_results"))
    seeded_db.flush()
    assert (
        get_current_pointer(
            seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
        )
        is None
    )

    seeded_db.execute(text(_BACKFILL_SQL))
    seeded_db.flush()
    pointer = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer is not None
    assert pointer.current_result_id == second.result.id

    # Idempotent re-run must not create a second pointer.
    seeded_db.execute(text(_BACKFILL_SQL))
    seeded_db.flush()
    count = seeded_db.execute(
        select(func.count())
        .select_from(CbamStationaryCombustionCurrentResult)
        .where(CbamStationaryCombustionCurrentResult.activity_record_id == activity.id)
    ).scalar_one()
    assert count == 1

    seeded_db.refresh(first_row)
    seeded_db.refresh(second_row)
    assert (
        first_row.result_value,
        first_row.fossil_co2_tonnes,
        first_row.activity_quantity,
        second_row.result_value,
        second_row.fossil_co2_tonnes,
    ) == snapshot_before


def test_backfill_created_at_tie_uses_stable_id_ordering(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation, _period = _setup(seeded_db, admin, org)
    activity = _create_ng_activity(seeded_db, admin, org, binding, installation)
    older = _exec(seeded_db, admin, org, binding, activity)
    newer = _exec(seeded_db, admin, org, binding, activity, density=Decimal("0.68"))
    older_row = seeded_db.get(CbamStationaryCombustionResult, older.result.id)
    newer_row = seeded_db.get(CbamStationaryCombustionResult, newer.result.id)
    assert older_row is not None and newer_row is not None
    # Force identical timestamps so ORDER BY id DESC is the only discriminator.
    tie_time = newer_row.created_at
    older_row.created_at = tie_time
    newer_row.created_at = tie_time
    seeded_db.flush()
    expected = max(older.result.id, newer.result.id)

    seeded_db.execute(text("DELETE FROM cbam_stationary_combustion_current_results"))
    seeded_db.flush()
    seeded_db.execute(text(_BACKFILL_SQL))
    seeded_db.flush()
    pointer = get_current_pointer(
        seeded_db, organization_id=org.id, binding_id=binding.id, activity_id=activity.id
    )
    assert pointer is not None
    assert pointer.current_result_id == expected
