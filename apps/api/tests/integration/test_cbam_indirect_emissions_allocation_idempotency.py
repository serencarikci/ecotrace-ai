"""Phase 8C IEA idempotency + real PostgreSQL concurrency."""

from __future__ import annotations

import threading
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from tests.cbam_iea_helpers import seed_workbook_ready_ie_allocation

from ecotrace.db.seed import DEMO_ORG_SLUG, run_seed
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.cn_catalog_seed import ensure_platform_cn_catalog
from ecotrace.modules.cbam.application.export_template_service import (
    ensure_internal_export_template,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.indirect_emissions_allocation_service import (
    IndirectEmissionsAllocationExecuteRequest,
    execute_indirect_emissions_allocation,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamIndirectEmissionsAllocationCurrent,
    CbamIndirectEmissionsAllocationResult,
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
            select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
        ).scalar_one()
        seed_workbook_ready_ie_allocation(db, admin, org)
        db.commit()
        binding_id = db.execute(
            text(
                """
SELECT reporting_period_binding_id
FROM cbam_purchased_electricity_current_results
WHERE organization_id = :oid
LIMIT 1
"""
            ),
            {"oid": org.id},
        ).scalar_one()
        return {
            "org_id": org.id,
            "admin_id": admin.id,
            "binding_id": binding_id,
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
            admin = db.get(User, ctx["admin_id"])
            barrier.wait(timeout=30)
            out = execute_indirect_emissions_allocation(
                db,
                admin,
                ctx["org_id"],
                ctx["binding_id"],
                IndirectEmissionsAllocationExecuteRequest(client_request_id=client_id),
            )
            results.append(out.result_id)
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
    assert results[0] == results[1]

    db = session_factory()
    try:
        count = (
            db.execute(
                select(CbamIndirectEmissionsAllocationResult).where(
                    CbamIndirectEmissionsAllocationResult.reporting_period_binding_id
                    == ctx["binding_id"],
                    CbamIndirectEmissionsAllocationResult.client_request_id == client_id,
                )
            )
            .scalars()
            .all()
        )
        assert len(count) == 1
        pointer = db.execute(
            select(CbamIndirectEmissionsAllocationCurrent).where(
                CbamIndirectEmissionsAllocationCurrent.reporting_period_binding_id
                == ctx["binding_id"]
            )
        ).scalar_one()
        assert pointer.current_result_id == results[0]
    finally:
        db.close()


def test_iea_migration_tables_exist(engine) -> None:
    with engine.connect() as conn:
        for table in (
            "cbam_indirect_emissions_allocation_results",
            "cbam_iea_monthly_basis_snapshots",
            "cbam_iea_source_snapshots",
            "cbam_iea_product_allocations",
            "cbam_indirect_emissions_allocation_current",
        ):
            exists = conn.execute(
                text("SELECT to_regclass(:t)"),
                {"t": table},
            ).scalar()
            assert exists == table
