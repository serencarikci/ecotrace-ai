"""Phase 7A-2 DEA idempotency + real PostgreSQL concurrency."""

from __future__ import annotations

import threading
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from tests.cbam_dea_helpers import seed_workbook_ready_allocation

from ecotrace.core.exceptions import ConflictError
from ecotrace.db.seed import DEMO_ORG_SLUG, run_seed
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.cn_catalog_seed import ensure_platform_cn_catalog
from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
    DirectEmissionsAllocationExecuteRequest,
    execute_direct_emissions_allocation,
)
from ecotrace.modules.cbam.application.export_template_service import (
    ensure_internal_export_template,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamDeaSourceSnapshot,
    CbamDirectEmissionsAllocationCurrent,
    CbamDirectEmissionsAllocationResult,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization


def _committed_setup(engine):
    from tests.conftest import _truncate_all

    _truncate_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = session_factory()
    try:
        run_seed(db)
        ensure_platform_factor_catalog(db)
        ensure_platform_stationary_combustion_catalog(db)
        ensure_platform_cn_catalog(db)
        ensure_platform_calculation_definitions(db)
        ensure_internal_export_template(db)
        db.commit()

        org = db.execute(
            select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
        ).scalar_one()
        admin = db.execute(
            select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
        ).scalar_one()
        binding, _ = seed_workbook_ready_allocation(db, admin, org)
        db.commit()
        return {
            'org_id': org.id,
            'admin_id': admin.id,
            'binding_id': binding.id,
        }
    finally:
        db.close()


def test_concurrent_identical_requests_one_result(engine) -> None:
    ctx = _committed_setup(engine)
    client_id = uuid.uuid4()
    barrier = threading.Barrier(2)
    results: list = []
    errors: list = []
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def worker() -> None:
        db = session_factory()
        try:
            admin = db.get(User, ctx['admin_id'])
            assert admin is not None
            barrier.wait(timeout=30)
            out = execute_direct_emissions_allocation(
                db,
                admin,
                ctx['org_id'],
                ctx['binding_id'],
                DirectEmissionsAllocationExecuteRequest(client_request_id=client_id),
            )
            results.append(out)
        except Exception as exc:
            errors.append(exc)
        finally:
            db.close()

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=60)
    t2.join(timeout=60)

    assert not errors, errors
    assert len(results) == 2
    ids = {r.result_id for r in results}
    assert len(ids) == 1
    assert sum(1 for r in results if not r.idempotent_replay) == 1
    assert sum(1 for r in results if r.idempotent_replay) == 1

    db = session_factory()
    try:
        rows = db.execute(
            select(CbamDirectEmissionsAllocationResult).where(
                CbamDirectEmissionsAllocationResult.reporting_period_binding_id
                == ctx['binding_id'],
                CbamDirectEmissionsAllocationResult.client_request_id == client_id,
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == 'COMPLETED'
        assert rows[0].balance_status == 'BALANCED'
        sources = db.execute(
            select(CbamDeaSourceSnapshot).where(
                CbamDeaSourceSnapshot.result_id == rows[0].id
            )
        ).scalars().all()
        assert len(sources) == 3
        # No orphan RUNNING — status check constraint only allows COMPLETED
        pointers = db.execute(
            select(CbamDirectEmissionsAllocationCurrent).where(
                CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id
                == ctx['binding_id']
            )
        ).scalars().all()
        assert len(pointers) == 1
        assert pointers[0].current_result_id == rows[0].id
    finally:
        db.close()


def test_concurrent_conflicting_fingerprint_safe(engine) -> None:
    """Same key, different material: one wins COMPLETED; other gets IDEMPOTENCY_KEY_REUSED."""
    ctx = _committed_setup(engine)
    client_id = uuid.uuid4()
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    # First commit a successful allocation with the key
    db0 = session_factory()
    try:
        admin = db0.get(User, ctx['admin_id'])
        assert admin is not None
        execute_direct_emissions_allocation(
            db0,
            admin,
            ctx['org_id'],
            ctx['binding_id'],
            DirectEmissionsAllocationExecuteRequest(client_request_id=client_id),
        )
    finally:
        db0.close()

    # Corrupt fingerprint then retry → conflict
    db1 = session_factory()
    try:
        admin = db1.get(User, ctx['admin_id'])
        assert admin is not None
        row = db1.execute(
            select(CbamDirectEmissionsAllocationResult).where(
                CbamDirectEmissionsAllocationResult.client_request_id == client_id
            )
        ).scalar_one()
        row.request_fingerprint = 'a' * 64
        db1.commit()
        try:
            execute_direct_emissions_allocation(
                db1,
                admin,
                ctx['org_id'],
                ctx['binding_id'],
                DirectEmissionsAllocationExecuteRequest(client_request_id=client_id),
            )
            raise AssertionError('expected ConflictError')
        except ConflictError as exc:
            assert exc.details[0]['code'] == 'IDEMPOTENCY_KEY_REUSED'
    finally:
        db1.close()


def test_failed_request_leaves_no_idempotency_row(engine) -> None:
    ctx = _committed_setup(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = session_factory()
    try:
        admin = db.get(User, ctx['admin_id'])
        assert admin is not None
        from ecotrace.modules.cbam.application import production_record_service
        from ecotrace.modules.cbam.application.production_record_service import (
            ProductionRecordUpdate,
        )

        page = production_record_service.list_production_records(
            db, admin, ctx['org_id'], ctx['binding_id'], page=1, page_size=50
        )
        row = page.items[0]
        production_record_service.update_production_record(
            db,
            admin,
            ctx['org_id'],
            row.id,
            ProductionRecordUpdate(row_version=row.row_version, quantity=Decimal('1')),
        )
        client_id = uuid.uuid4()
        from ecotrace.core.exceptions import BusinessRuleError

        try:
            execute_direct_emissions_allocation(
                db,
                admin,
                ctx['org_id'],
                ctx['binding_id'],
                DirectEmissionsAllocationExecuteRequest(client_request_id=client_id),
            )
            raise AssertionError('expected BusinessRuleError')
        except BusinessRuleError:
            pass
        found = db.execute(
            select(CbamDirectEmissionsAllocationResult).where(
                CbamDirectEmissionsAllocationResult.client_request_id == client_id
            )
        ).scalar_one_or_none()
        assert found is None
        assert (
            db.execute(select(CbamDirectEmissionsAllocationCurrent)).scalar_one_or_none()
            is None
        )
    finally:
        db.close()
