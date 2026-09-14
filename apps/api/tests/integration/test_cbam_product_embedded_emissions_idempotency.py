"""Phase 10C roll-up idempotency, current-pointer safety and real PostgreSQL concurrency."""

from __future__ import annotations

import threading
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from tests.cbam_pee_helpers import seed_ready_rollup

from ecotrace.core.exceptions import BusinessRuleError, ConflictError
from ecotrace.db.seed import DEMO_ORG_SLUG, run_seed
from ecotrace.modules.cbam.application import purchased_precursor_service
from ecotrace.modules.cbam.application.calculation_service import (
    ensure_platform_calculation_definitions,
)
from ecotrace.modules.cbam.application.cn_catalog_seed import ensure_platform_cn_catalog
from ecotrace.modules.cbam.application.export_template_service import (
    ensure_internal_export_template,
)
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.precursor_default_catalog_seed import (
    ensure_platform_precursor_default_catalog,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_constants import METHODOLOGY_CODE
from ecotrace.modules.cbam.application.product_embedded_emissions_service import (
    ProductEmbeddedEmissionsExecuteRequest,
    execute_product_embedded_emissions,
)
from ecotrace.modules.cbam.application.purchased_precursor_service import (
    PurchasedPrecursorUpdate,
)
from ecotrace.modules.cbam.application.stationary_combustion_catalog_seed import (
    ensure_platform_stationary_combustion_catalog,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamProductEmbeddedEmissionsCurrent,
    CbamProductEmbeddedEmissionsPrecursorContribution,
    CbamProductEmbeddedEmissionsProduct,
    CbamProductEmbeddedEmissionsResult,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization


def _committed_setup(engine) -> dict:
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
        ensure_platform_precursor_default_catalog(db)
        ensure_internal_export_template(db)
        db.commit()

        org = db.execute(
            select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
        ).scalar_one()
        admin = db.execute(
            select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
        ).scalar_one()
        scenario = seed_ready_rollup(db, admin, org)
        db.commit()
        return {
            "org_id": org.id,
            "admin_id": admin.id,
            "binding_id": scenario.binding.id,
            "precursor_id": scenario.precursor_id,
        }
    finally:
        db.close()


def _session(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def test_concurrent_identical_requests_produce_one_result(engine) -> None:
    ctx = _committed_setup(engine)
    client_id = uuid.uuid4()
    barrier = threading.Barrier(2)
    results: list = []
    errors: list = []

    def worker() -> None:
        db = _session(engine)
        try:
            admin = db.get(User, ctx["admin_id"])
            assert admin is not None
            barrier.wait(timeout=30)
            results.append(
                execute_product_embedded_emissions(
                    db,
                    admin,
                    ctx["org_id"],
                    ctx["binding_id"],
                    ProductEmbeddedEmissionsExecuteRequest(
                        client_request_id=client_id, methodology_code=METHODOLOGY_CODE
                    ),
                )
            )
        except Exception as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    assert not errors, errors
    assert len(results) == 2
    assert len({r.result_id for r in results}) == 1
    assert sum(1 for r in results if not r.idempotent_replay) == 1
    assert sum(1 for r in results if r.idempotent_replay) == 1

    db = _session(engine)
    try:
        rows = (
            db.execute(
                select(CbamProductEmbeddedEmissionsResult).where(
                    CbamProductEmbeddedEmissionsResult.reporting_period_binding_id
                    == ctx["binding_id"],
                    CbamProductEmbeddedEmissionsResult.client_request_id == client_id,
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].status == "COMPLETED"

        products = (
            db.execute(
                select(CbamProductEmbeddedEmissionsProduct).where(
                    CbamProductEmbeddedEmissionsProduct.result_id == rows[0].id
                )
            )
            .scalars()
            .all()
        )
        assert len(products) == 1
        contributions = (
            db.execute(
                select(CbamProductEmbeddedEmissionsPrecursorContribution).where(
                    CbamProductEmbeddedEmissionsPrecursorContribution.result_id == rows[0].id
                )
            )
            .scalars()
            .all()
        )
        assert len(contributions) == 1

        pointers = (
            db.execute(
                select(CbamProductEmbeddedEmissionsCurrent).where(
                    CbamProductEmbeddedEmissionsCurrent.reporting_period_binding_id
                    == ctx["binding_id"]
                )
            )
            .scalars()
            .all()
        )
        assert len(pointers) == 1
        assert pointers[0].current_result_id == rows[0].id
    finally:
        db.close()


def test_same_key_with_different_material_inputs_conflicts(engine) -> None:
    ctx = _committed_setup(engine)
    client_id = uuid.uuid4()

    db0 = _session(engine)
    try:
        admin = db0.get(User, ctx["admin_id"])
        assert admin is not None
        execute_product_embedded_emissions(
            db0,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ProductEmbeddedEmissionsExecuteRequest(
                client_request_id=client_id, methodology_code=METHODOLOGY_CODE
            ),
        )
    finally:
        db0.close()

    db1 = _session(engine)
    try:
        admin = db1.get(User, ctx["admin_id"])
        assert admin is not None
        precursor = purchased_precursor_service.get_purchased_precursor(
            db1, admin, ctx["org_id"], ctx["binding_id"], ctx["precursor_id"]
        )
        purchased_precursor_service.update_purchased_precursor_draft(
            db1,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ctx["precursor_id"],
            PurchasedPrecursorUpdate(
                row_version=precursor.row_version,
                specific_direct_embedded_emissions=Decimal("0.9"),
            ),
        )
        db1.commit()
        try:
            execute_product_embedded_emissions(
                db1,
                admin,
                ctx["org_id"],
                ctx["binding_id"],
                ProductEmbeddedEmissionsExecuteRequest(
                    client_request_id=client_id, methodology_code=METHODOLOGY_CODE
                ),
            )
            raise AssertionError("expected ConflictError")
        except ConflictError as exc:
            assert exc.details[0]["code"] == "IDEMPOTENCY_KEY_REUSED"
    finally:
        db1.close()


def test_failed_execution_preserves_the_previous_current_pointer(engine) -> None:
    ctx = _committed_setup(engine)
    db = _session(engine)
    try:
        admin = db.get(User, ctx["admin_id"])
        assert admin is not None
        first = execute_product_embedded_emissions(
            db,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ProductEmbeddedEmissionsExecuteRequest(
                client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE
            ),
        )

        # Unbalance the precursor so the binding is no longer ready.
        precursor = purchased_precursor_service.get_purchased_precursor(
            db, admin, ctx["org_id"], ctx["binding_id"], ctx["precursor_id"]
        )
        purchased_precursor_service.update_purchased_precursor_draft(
            db,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ctx["precursor_id"],
            PurchasedPrecursorUpdate(row_version=precursor.row_version, quantity=Decimal("9")),
        )
        db.commit()

        failed_key = uuid.uuid4()
        try:
            execute_product_embedded_emissions(
                db,
                admin,
                ctx["org_id"],
                ctx["binding_id"],
                ProductEmbeddedEmissionsExecuteRequest(
                    client_request_id=failed_key, methodology_code=METHODOLOGY_CODE
                ),
            )
            raise AssertionError("expected BusinessRuleError")
        except BusinessRuleError:
            pass

        assert (
            db.execute(
                select(CbamProductEmbeddedEmissionsResult).where(
                    CbamProductEmbeddedEmissionsResult.client_request_id == failed_key
                )
            ).scalar_one_or_none()
            is None
        )
        pointer = db.execute(
            select(CbamProductEmbeddedEmissionsCurrent).where(
                CbamProductEmbeddedEmissionsCurrent.reporting_period_binding_id == ctx["binding_id"]
            )
        ).scalar_one()
        assert pointer.current_result_id == first.result_id
    finally:
        db.close()


def test_successful_reexecution_advances_the_current_pointer(engine) -> None:
    ctx = _committed_setup(engine)
    db = _session(engine)
    try:
        admin = db.get(User, ctx["admin_id"])
        assert admin is not None
        first = execute_product_embedded_emissions(
            db,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ProductEmbeddedEmissionsExecuteRequest(
                client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE
            ),
        )
        precursor = purchased_precursor_service.get_purchased_precursor(
            db, admin, ctx["org_id"], ctx["binding_id"], ctx["precursor_id"]
        )
        purchased_precursor_service.update_purchased_precursor_draft(
            db,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ctx["precursor_id"],
            PurchasedPrecursorUpdate(
                row_version=precursor.row_version,
                specific_direct_embedded_emissions=Decimal("1"),
            ),
        )
        db.commit()
        second = execute_product_embedded_emissions(
            db,
            admin,
            ctx["org_id"],
            ctx["binding_id"],
            ProductEmbeddedEmissionsExecuteRequest(
                client_request_id=uuid.uuid4(), methodology_code=METHODOLOGY_CODE
            ),
        )
        assert second.result_id != first.result_id
        # 3 t × 1.0 instead of 3 t × 0.5 → the direct total grows by exactly 1.5 tCO2e.
        assert second.total_direct_tco2e - first.total_direct_tco2e == Decimal("1.50000000")

        pointer = db.execute(
            select(CbamProductEmbeddedEmissionsCurrent).where(
                CbamProductEmbeddedEmissionsCurrent.reporting_period_binding_id == ctx["binding_id"]
            )
        ).scalar_one()
        assert pointer.current_result_id == second.result_id
    finally:
        db.close()
