"""Purchased-electricity indirect-emissions allocation execution.

Two-stage engine: monthly E/D attribution of immutable PE snapshots, then product split.
Reuses Phase 7A-2 pure math helpers; keeps separate typed snapshots for electricity/tCO2e.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ecotrace.modules.cbam.application.calculation_math import quantize_result
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_constants import (
    BALANCE_BALANCED,
    EXECUTION_STATUS_COMPLETED,
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    RESULT_UNIT_ELECTRICITY,
    RESULT_UNIT_EMISSIONS,
    WORKBOOK_FILENAME,
    WORKBOOK_FORMULA_REFS,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_idempotency import (
    build_indirect_emissions_allocation_fingerprint,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_math import (
    ZERO,
    allocate_pool_with_largest_remainder,
    attribute_measure,
    monthly_cbam_share,
)
from ecotrace.modules.cbam.application.monthly_production_basis_service import (
    canonical_month_start,
    get_monthly_production_basis_summary,
    iter_expected_months,
    to_tonnes,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.production_profile_link import (
    compute_profile_link_state,
    is_allocation_eligible_link,
)
from ecotrace.modules.cbam.application.purchased_electricity_constants import (
    ELECTRICITY_ACTIVITY_TYPE,
    ELECTRICITY_QUANTITY_UNITS,
)
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    compute_stale_reasons as compute_pe_stale_reasons,
)
from ecotrace.modules.cbam.application.purchased_electricity_service import (
    get_purchased_electricity_summary,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamIeaMonthlyBasisSnapshot,
    CbamIeaProductAllocation,
    CbamIeaSourceSnapshot,
    CbamIndirectEmissionsAllocationCurrent,
    CbamIndirectEmissionsAllocationResult,
    CbamMonthlyProductionBasis,
    CbamProductionRecord,
    CbamProductProfileVersion,
    CbamPurchasedElectricityCurrentResult,
    CbamPurchasedElectricityResult,
    CbamReportingPeriodBinding,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

ReadinessStatus = Literal["READY", "NOT_READY"]


class IndirectEmissionsAllocationExecuteRequest(CamelModel):
    client_request_id: uuid.UUID


class IndirectEmissionsAllocationExecutionResponse(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    status: str
    methodology_code: str
    methodology_version: str
    balance_status: str
    facility_electricity_mwh: Decimal
    cbam_electricity_mwh: Decimal
    non_cbam_electricity_mwh: Decimal
    allocated_electricity_mwh: Decimal
    remaining_electricity_mwh: Decimal
    facility_indirect_emissions_tco2e: Decimal
    cbam_indirect_emissions_tco2e: Decimal
    non_cbam_indirect_emissions_tco2e: Decimal
    allocated_indirect_emissions_tco2e: Decimal
    remaining_indirect_emissions_tco2e: Decimal
    exported_electricity_mwh: Decimal | None
    electricity_unit: str
    emissions_unit: str
    client_request_id: uuid.UUID
    idempotent_replay: bool
    created_at: datetime


class IndirectEmissionsAllocationReadiness(CamelModel):
    status: ReadinessStatus
    allocation_ready: bool
    blocking_issue_codes: list[str]
    purchased_electricity_status: str
    monthly_production_basis_status: str
    production_profile_status: str
    production_reconciliation_status: str
    source_result_count: int
    month_count: int
    participating_production_record_count: int
    product_profile_group_count: int
    current_allocation_id: uuid.UUID | None
    current_allocation_stale: bool
    stale_reason_codes: list[str]


class IndirectEmissionsAllocationResultSummary(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    methodology_code: str
    methodology_version: str
    status: str
    balance_status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    facility_electricity_mwh: Decimal
    cbam_electricity_mwh: Decimal
    non_cbam_electricity_mwh: Decimal
    allocated_electricity_mwh: Decimal
    remaining_electricity_mwh: Decimal
    facility_indirect_emissions_tco2e: Decimal
    cbam_indirect_emissions_tco2e: Decimal
    allocated_indirect_emissions_tco2e: Decimal
    remaining_indirect_emissions_tco2e: Decimal
    exported_electricity_mwh: Decimal | None
    electricity_unit: str
    emissions_unit: str
    created_at: datetime


class IndirectEmissionsAllocationPeriodSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    current_result_id: uuid.UUID | None
    current_is_stale: bool
    stale_reason_codes: list[str]
    facility_electricity_mwh: Decimal | None
    cbam_electricity_mwh: Decimal | None
    non_cbam_electricity_mwh: Decimal | None
    allocated_electricity_mwh: Decimal | None
    remaining_electricity_mwh: Decimal | None
    facility_indirect_emissions_tco2e: Decimal | None
    cbam_indirect_emissions_tco2e: Decimal | None
    allocated_indirect_emissions_tco2e: Decimal | None
    remaining_indirect_emissions_tco2e: Decimal | None
    exported_electricity_mwh: Decimal | None
    electricity_unit: str
    emissions_unit: str
    balance_status: str | None
    totals_by_month: dict[str, Any]
    totals_by_product_profile: list[dict[str, Any]]


class IndirectEmissionsAllocationResultDetail(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    methodology_version: str
    workbook_filename: str
    workbook_sha256: str
    workbook_formula_refs: str
    client_request_id: uuid.UUID
    request_fingerprint: str
    status: str
    balance_status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    facility_electricity_mwh_raw: Decimal
    cbam_electricity_mwh_raw: Decimal
    non_cbam_electricity_mwh_raw: Decimal
    facility_electricity_mwh: Decimal
    cbam_electricity_mwh: Decimal
    non_cbam_electricity_mwh: Decimal
    allocated_electricity_mwh: Decimal
    remaining_electricity_mwh: Decimal
    facility_indirect_emissions_tco2e_raw: Decimal
    cbam_indirect_emissions_tco2e_raw: Decimal
    non_cbam_indirect_emissions_tco2e_raw: Decimal
    facility_indirect_emissions_tco2e: Decimal
    cbam_indirect_emissions_tco2e: Decimal
    non_cbam_indirect_emissions_tco2e: Decimal
    allocated_indirect_emissions_tco2e: Decimal
    remaining_indirect_emissions_tco2e: Decimal
    exported_electricity_mwh: Decimal | None
    electricity_unit: str
    emissions_unit: str
    source_result_count: int
    month_count: int
    participating_production_record_count: int
    product_profile_group_count: int
    totals_by_month: dict[str, Any]
    monthly_basis: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    products: list[dict[str, Any]]
    created_at: datetime
    created_by_user_id: uuid.UUID | None


def _period(db: Session, organization_id: uuid.UUID, binding: CbamReportingPeriodBinding) -> Any:
    return require_reporting_period_in_organization(
        db, organization_id=organization_id, reporting_period_id=binding.reporting_period_id
    )


def _dedupe_codes(codes: list[str]) -> list[str]:
    out: list[str] = []
    for c in codes:
        if c not in out:
            out.append(c)
    return out


def _current_pointer(
    db: Session, *, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> CbamIndirectEmissionsAllocationCurrent | None:
    return db.execute(
        select(CbamIndirectEmissionsAllocationCurrent).where(
            CbamIndirectEmissionsAllocationCurrent.organization_id == organization_id,
            CbamIndirectEmissionsAllocationCurrent.reporting_period_binding_id == binding_id,
            CbamIndirectEmissionsAllocationCurrent.methodology_code == METHODOLOGY_CODE,
        )
    ).scalar_one_or_none()


def _set_current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> None:
    stmt = pg_insert(CbamIndirectEmissionsAllocationCurrent).values(
        id=uuid.uuid4(),
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE,
        current_result_id=result_id,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[
            "organization_id",
            "reporting_period_binding_id",
            "methodology_code",
        ],
        set_={"current_result_id": result_id, "updated_at": datetime.now(UTC)},
    )
    db.execute(stmt)


def _find_by_client_request(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> CbamIndirectEmissionsAllocationResult | None:
    return db.execute(
        select(CbamIndirectEmissionsAllocationResult).where(
            CbamIndirectEmissionsAllocationResult.organization_id == organization_id,
            CbamIndirectEmissionsAllocationResult.reporting_period_binding_id == binding_id,
            CbamIndirectEmissionsAllocationResult.client_request_id == client_request_id,
        )
    ).scalar_one_or_none()


def _pe_current_pointers(
    db: Session, *, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> dict[uuid.UUID, uuid.UUID]:
    rows = db.execute(
        select(CbamPurchasedElectricityCurrentResult).where(
            CbamPurchasedElectricityCurrentResult.organization_id == organization_id,
            CbamPurchasedElectricityCurrentResult.reporting_period_binding_id == binding_id,
        )
    ).scalars()
    return {r.activity_record_id: r.current_result_id for r in rows}


def _resolve_context(
    db: Session, user: User, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> dict[str, Any]:
    binding = get_binding_for_org(db, organization_id, binding_id)
    period = _period(db, organization_id, binding)
    expected_months = iter_expected_months(period.start_date, period.end_date)
    blocking: list[str] = []

    pe_summary = get_purchased_electricity_summary(db, user, organization_id, binding_id)
    pe_status = pe_summary.readiness_status
    if pe_status != "READY":
        if pe_summary.stale_result_count > 0 or pe_status == "STALE":
            blocking.append("INDIRECT_EMISSIONS_STALE")
        else:
            blocking.append("INDIRECT_EMISSIONS_NOT_READY")

    pointer_map = _pe_current_pointers(db, organization_id=organization_id, binding_id=binding_id)
    activity_ids = list(pointer_map.keys())
    activities: dict[uuid.UUID, CbamActivityRecord] = {}
    if activity_ids:
        activities = {
            a.id: a
            for a in db.execute(
                select(CbamActivityRecord).where(CbamActivityRecord.id.in_(activity_ids))
            ).scalars()
        }
    result_ids = list(pointer_map.values())
    results: dict[uuid.UUID, CbamPurchasedElectricityResult] = {}
    if result_ids:
        results = {
            r.id: r
            for r in db.execute(
                select(CbamPurchasedElectricityResult).where(
                    CbamPurchasedElectricityResult.id.in_(result_ids)
                )
            ).scalars()
        }

    sources: list[tuple[CbamActivityRecord, CbamPurchasedElectricityResult, date]] = []
    for activity_id, result_id in pointer_map.items():
        activity = activities.get(activity_id)
        result = results.get(result_id)
        if activity is None or result is None:
            blocking.append("INDIRECT_EMISSIONS_NOT_READY")
            continue
        if activity.status != "active":
            continue
        if activity.activity_type != ELECTRICITY_ACTIVITY_TYPE:
            continue
        if activity.unit not in ELECTRICITY_QUANTITY_UNITS:
            continue
        if activity.activity_date is None:
            blocking.append("ELECTRICITY_ACTIVITY_DATE_REQUIRED")
            continue
        month = canonical_month_start(activity.activity_date)
        if month not in expected_months:
            blocking.append("ELECTRICITY_MONTH_NOT_COVERED")
            continue
        if compute_pe_stale_reasons(activity, result):
            blocking.append("INDIRECT_EMISSIONS_STALE")
            continue
        sources.append((activity, result, month))

    if pe_status == "READY" and not sources:
        blocking.append("INDIRECT_EMISSIONS_NOT_READY")

    mb_summary = get_monthly_production_basis_summary(db, user, organization_id, binding_id)
    mb_status = mb_summary.status
    if not mb_summary.allocation_basis_ready:
        blocking.append("MONTHLY_PRODUCTION_BASIS_NOT_READY")
        for code in mb_summary.blocking_issue_codes:
            if code not in blocking:
                blocking.append(code)

    basis_rows = {
        r.month_start: r
        for r in db.execute(
            select(CbamMonthlyProductionBasis).where(
                CbamMonthlyProductionBasis.organization_id == organization_id,
                CbamMonthlyProductionBasis.reporting_period_binding_id == binding_id,
            )
        ).scalars()
    }
    month_shares: dict[date, Decimal] = {}
    for month in expected_months:
        row = basis_rows.get(month)
        if row is None or row.total_production_quantity is None or row.cbam_quantity is None:
            blocking.append("MONTHLY_PRODUCTION_BASIS_NOT_READY")
            continue
        try:
            d_t = to_tonnes(row.total_production_quantity, row.quantity_unit)
            e_t = to_tonnes(row.cbam_quantity, row.quantity_unit)
            month_shares[month] = monthly_cbam_share(
                total_production_tonnes=d_t, cbam_quantity_tonnes=e_t
            )
        except ValueError as exc:
            if str(exc) == "TOTAL_PRODUCTION_MUST_BE_POSITIVE":
                blocking.append("TOTAL_PRODUCTION_MUST_BE_POSITIVE")
            else:
                blocking.append("MONTHLY_PRODUCTION_BASIS_NOT_READY")
        except Exception:
            blocking.append("MONTHLY_PRODUCTION_BASIS_NOT_READY")

    recon_status = "EXACT_MATCH"
    for item in mb_summary.production_reconciliation:
        if item.reconciliation_status == "MISMATCH":
            blocking.append("PRODUCTION_RECONCILIATION_MISMATCH")
            recon_status = "MISMATCH"
        elif item.reconciliation_status == "UNAVAILABLE":
            blocking.append("PRODUCTION_RECONCILIATION_UNAVAILABLE")
            if recon_status != "MISMATCH":
                recon_status = "UNAVAILABLE"

    prod_rows = list(
        db.execute(
            select(CbamProductionRecord).where(
                CbamProductionRecord.organization_id == organization_id,
                CbamProductionRecord.reporting_period_binding_id == binding_id,
                CbamProductionRecord.status == "active",
            )
        ).scalars()
    )
    eligible: list[tuple[CbamProductionRecord, CbamProductProfileVersion, Decimal]] = []
    profile_status = "READY"
    for prod in prod_rows:
        if prod.production_date is None:
            blocking.append("PRODUCTION_DATE_REQUIRED")
            profile_status = "NOT_READY"
            continue
        link_status, _codes, profile = compute_profile_link_state(db, prod)
        if link_status == "MISSING":
            blocking.append("PRODUCTION_PROFILE_LINK_MISSING")
            profile_status = "NOT_READY"
            continue
        if link_status == "INVALID" or not is_allocation_eligible_link(link_status):
            blocking.append("PRODUCTION_PROFILE_LINK_INVALID")
            profile_status = "NOT_READY"
            continue
        if profile is None:
            blocking.append("PRODUCTION_PROFILE_LINK_MISSING")
            profile_status = "NOT_READY"
            continue
        try:
            tonnes = to_tonnes(prod.quantity, prod.unit)
        except Exception:
            blocking.append("INCOMPATIBLE_PRODUCTION_UNIT")
            profile_status = "NOT_READY"
            continue
        if tonnes <= 0:
            blocking.append("NO_ELIGIBLE_PRODUCTION")
            profile_status = "NOT_READY"
            continue
        eligible.append((prod, profile, tonnes))

    groups: dict[uuid.UUID, dict[str, Any]] = {}
    for prod, profile, tonnes in eligible:
        g = groups.setdefault(
            profile.id,
            {
                "profile": profile,
                "product_id": profile.product_id,
                "qty": ZERO,
                "records": [],
                "snapshots": [],
            },
        )
        g["qty"] += tonnes
        g["records"].append(str(prod.id))
        g["snapshots"].append(
            {
                "productionRecordId": str(prod.id),
                "quantity": str(prod.quantity),
                "unit": prod.unit,
                "productionDate": (
                    prod.production_date.isoformat() if prod.production_date else None
                ),
                "normalizedTonnes": str(tonnes),
                "productProfileVersionId": str(profile.id),
            }
        )

    for g in groups.values():
        paired = sorted(
            zip(g["records"], g["snapshots"], strict=True),
            key=lambda t: t[0],
        )
        g["records"] = [r for r, _ in paired]
        g["snapshots"] = [s for _, s in paired]

    if not groups:
        blocking.append("NO_ELIGIBLE_PRODUCTION")
        profile_status = "NOT_READY"
    denom = sum((g["qty"] for g in groups.values()), ZERO)
    if groups and denom <= 0:
        blocking.append("ZERO_ALLOCATION_DENOMINATOR")

    return {
        "binding": binding,
        "expected_months": expected_months,
        "blocking": _dedupe_codes(blocking),
        "pe_status": pe_status,
        "mb_status": mb_status,
        "mb_summary": mb_summary,
        "recon_status": recon_status,
        "profile_status": profile_status,
        "sources": sources,
        "basis_rows": basis_rows,
        "month_shares": month_shares,
        "groups": groups,
        "denom": denom,
        "eligible_count": len(eligible),
    }


def compute_allocation_stale_reasons(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result: CbamIndirectEmissionsAllocationResult,
) -> list[str]:
    reasons: list[str] = []
    if (
        result.methodology_code != METHODOLOGY_CODE
        or result.methodology_version != METHODOLOGY_VERSION
        or result.workbook_sha256 != WORKBOOK_SHA256
    ):
        reasons.append("METHODOLOGY_OR_WORKBOOK_CHANGED")

    ctx = _resolve_context(db, user, organization_id, binding_id)
    live_source_ids = {r.id for _, r, _ in ctx["sources"]}
    snap_sources = list(
        db.execute(
            select(CbamIeaSourceSnapshot).where(CbamIeaSourceSnapshot.result_id == result.id)
        ).scalars()
    )
    snap_source_ids = {s.source_result_id for s in snap_sources}
    if live_source_ids != snap_source_ids:
        reasons.append("SOURCE_CURRENT_RESULT_CHANGED")

    pointer_map = _pe_current_pointers(db, organization_id=organization_id, binding_id=binding_id)
    for snap in snap_sources:
        if pointer_map.get(snap.activity_record_id) != snap.source_result_id:
            reasons.append("SOURCE_CURRENT_RESULT_CHANGED")
        activity = db.get(CbamActivityRecord, snap.activity_record_id)
        pe = db.get(CbamPurchasedElectricityResult, snap.source_result_id)
        if activity is None or pe is None:
            reasons.append("SOURCE_CURRENT_RESULT_CHANGED")
        elif compute_pe_stale_reasons(activity, pe):
            reasons.append("INDIRECT_EMISSIONS_STALE")
        elif (
            activity.quantity != snap.activity_quantity
            or activity.unit != snap.activity_unit
            or activity.activity_date != snap.activity_date
            or pe.factor_value != snap.factor_value
            or pe.factor_unit != snap.factor_unit
            or pe.factor_source_mode != snap.factor_source_mode
            or pe.electricity_mwh != snap.electricity_mwh
            or pe.indirect_emissions_tco2e != snap.facility_indirect_emissions_tco2e
        ):
            reasons.append("SOURCE_ACTIVITY_MATERIAL_CHANGED")

    snap_basis = list(
        db.execute(
            select(CbamIeaMonthlyBasisSnapshot).where(
                CbamIeaMonthlyBasisSnapshot.result_id == result.id
            )
        ).scalars()
    )
    live_basis = ctx["basis_rows"]
    snap_basis_ids = {b.basis_record_id for b in snap_basis}
    live_basis_ids = {r.id for month, r in live_basis.items() if month in ctx["month_shares"]}
    if snap_basis_ids != live_basis_ids:
        reasons.append("MONTHLY_PRODUCTION_BASIS_CHANGED")
    for sb in snap_basis:
        live = live_basis.get(sb.month_start)
        if live is None:
            reasons.append("MONTHLY_PRODUCTION_BASIS_CHANGED")
            continue
        if (
            live.row_version != sb.basis_row_version
            or live.total_production_quantity != sb.total_production_quantity
            or live.cbam_quantity != sb.cbam_quantity
            or live.quantity_unit != sb.quantity_unit
        ):
            reasons.append("MONTHLY_PRODUCTION_BASIS_CHANGED")

    snap_products = list(
        db.execute(
            select(CbamIeaProductAllocation).where(CbamIeaProductAllocation.result_id == result.id)
        ).scalars()
    )
    live_prod_ids: set[str] = set()
    for g in ctx["groups"].values():
        live_prod_ids.update(g["records"])
    snap_prod_ids: set[str] = set()
    for sp in snap_products:
        snap_prod_ids.update(str(x) for x in sp.production_record_ids)
    if live_prod_ids != snap_prod_ids:
        reasons.append("PRODUCTION_SET_CHANGED")

    for sp in snap_products:
        for snap in sp.production_quantity_snapshots:
            pid = uuid.UUID(snap["productionRecordId"])
            prod = db.get(CbamProductionRecord, pid)
            if prod is None or prod.status != "active":
                reasons.append("PRODUCTION_MATERIAL_CHANGED")
                continue
            if (
                str(prod.quantity) != snap["quantity"]
                or prod.unit != snap["unit"]
                or (prod.production_date.isoformat() if prod.production_date else None)
                != snap.get("productionDate")
            ):
                reasons.append("PRODUCTION_MATERIAL_CHANGED")
            # Linked profile version id must match snapshot (newer publication alone ≠ stale).
            if str(prod.product_profile_version_id) != snap.get("productProfileVersionId"):
                reasons.append("PRODUCTION_PROFILE_LINK_INVALID")

    return _dedupe_codes(reasons)


def get_indirect_emissions_allocation_readiness(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> IndirectEmissionsAllocationReadiness:
    require_cbam_view(db, user, organization_id)
    ctx = _resolve_context(db, user, organization_id, binding_id)
    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    current_id = pointer.current_result_id if pointer else None
    stale_codes: list[str] = []
    current_stale = False
    if pointer is not None:
        result = db.get(CbamIndirectEmissionsAllocationResult, pointer.current_result_id)
        if result is not None:
            stale_codes = compute_allocation_stale_reasons(
                db, user, organization_id, binding_id, result
            )
            current_stale = bool(stale_codes)
    ready = len(ctx["blocking"]) == 0
    return IndirectEmissionsAllocationReadiness(
        status="READY" if ready else "NOT_READY",
        allocation_ready=ready,
        blocking_issue_codes=ctx["blocking"],
        purchased_electricity_status=ctx["pe_status"],
        monthly_production_basis_status=ctx["mb_status"],
        production_profile_status=ctx["profile_status"],
        production_reconciliation_status=ctx["recon_status"],
        source_result_count=len(ctx["sources"]),
        month_count=len(ctx["expected_months"]),
        participating_production_record_count=ctx["eligible_count"],
        product_profile_group_count=len(ctx["groups"]),
        current_allocation_id=current_id,
        current_allocation_stale=current_stale,
        stale_reason_codes=stale_codes,
    )


def _execution_response(
    result: CbamIndirectEmissionsAllocationResult, *, idempotent_replay: bool
) -> IndirectEmissionsAllocationExecutionResponse:
    return IndirectEmissionsAllocationExecutionResponse(
        result_id=result.id,
        run_id=result.id,
        status=result.status,
        methodology_code=result.methodology_code,
        methodology_version=result.methodology_version,
        balance_status=result.balance_status,
        facility_electricity_mwh=result.facility_electricity_mwh,
        cbam_electricity_mwh=result.cbam_electricity_mwh,
        non_cbam_electricity_mwh=result.non_cbam_electricity_mwh,
        allocated_electricity_mwh=result.allocated_electricity_mwh,
        remaining_electricity_mwh=result.remaining_electricity_mwh,
        facility_indirect_emissions_tco2e=result.facility_indirect_emissions_tco2e,
        cbam_indirect_emissions_tco2e=result.cbam_indirect_emissions_tco2e,
        non_cbam_indirect_emissions_tco2e=result.non_cbam_indirect_emissions_tco2e,
        allocated_indirect_emissions_tco2e=result.allocated_indirect_emissions_tco2e,
        remaining_indirect_emissions_tco2e=result.remaining_indirect_emissions_tco2e,
        exported_electricity_mwh=result.exported_electricity_mwh,
        electricity_unit=result.electricity_unit,
        emissions_unit=result.emissions_unit,
        client_request_id=result.client_request_id,
        idempotent_replay=idempotent_replay,
        created_at=result.created_at,
    )


def execute_indirect_emissions_allocation(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: IndirectEmissionsAllocationExecuteRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> IndirectEmissionsAllocationExecutionResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)

    ctx = _resolve_context(db, user, organization_id, binding_id)
    if ctx["blocking"]:
        raise BusinessRuleError(
            "Indirect-emissions allocation is not ready.",
            details=[{"code": c} for c in ctx["blocking"]],
        )

    source_result_ids = [r.id for _, r, _ in ctx["sources"]]
    source_material = [
        (
            r.id,
            r.activity_quantity,
            r.activity_unit,
            r.electricity_mwh,
            r.factor_source_mode,
            r.indirect_emissions_tco2e,
        )
        for _, r, _ in ctx["sources"]
    ]
    monthly_basis_fp = []
    for month, row in sorted(ctx["basis_rows"].items(), key=lambda t: t[0]):
        if month not in ctx["month_shares"]:
            continue
        assert row.total_production_quantity is not None and row.cbam_quantity is not None
        monthly_basis_fp.append(
            (
                row.id,
                row.row_version,
                month.isoformat(),
                row.total_production_quantity,
                row.cbam_quantity,
                row.quantity_unit,
            )
        )
    production_fp = []
    for g in ctx["groups"].values():
        for snap in g["snapshots"]:
            production_fp.append(
                (
                    uuid.UUID(snap["productionRecordId"]),
                    Decimal(snap["quantity"]),
                    snap["unit"],
                    snap["productionDate"] or "-",
                    str(g["profile"].id),
                )
            )

    fingerprint = build_indirect_emissions_allocation_fingerprint(
        organization_id=organization_id,
        binding_id=binding_id,
        source_result_ids=source_result_ids,
        source_material=source_material,
        monthly_basis=monthly_basis_fp,
        production=production_fp,
    )

    existing = _find_by_client_request(
        db,
        organization_id=organization_id,
        binding_id=binding_id,
        client_request_id=payload.client_request_id,
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise ConflictError(
                "This client request id was already used with different inputs.",
                details=[{"code": "IDEMPOTENCY_KEY_REUSED"}],
            )
        return _execution_response(existing, idempotent_replay=True)

    facility_mwh_raw = ZERO
    cbam_mwh_raw = ZERO
    facility_em_raw = ZERO
    cbam_em_raw = ZERO
    exported_total = ZERO
    has_exported = False
    source_rows: list[dict[str, Any]] = []
    totals_by_month: dict[str, dict[str, str]] = {}

    for activity, result, month in ctx["sources"]:
        share = ctx["month_shares"][month]
        mwh = attribute_measure(result.electricity_mwh, share)
        em = attribute_measure(result.indirect_emissions_tco2e, share)
        facility_mwh_raw += mwh.facility
        cbam_mwh_raw += mwh.cbam
        facility_em_raw += em.facility
        cbam_em_raw += em.cbam
        month_key = month.isoformat()
        bucket = totals_by_month.setdefault(
            month_key,
            {
                "cbamElectricityMwh": "0",
                "cbamIndirectEmissionsTco2e": "0",
            },
        )
        bucket["cbamElectricityMwh"] = str(Decimal(bucket["cbamElectricityMwh"]) + mwh.cbam)
        bucket["cbamIndirectEmissionsTco2e"] = str(
            Decimal(bucket["cbamIndirectEmissionsTco2e"]) + em.cbam
        )
        if result.exported_electricity_mwh is not None:
            exported_total += result.exported_electricity_mwh
            has_exported = True
        source_rows.append(
            {
                "activity": activity,
                "result": result,
                "month": month,
                "share": share,
                "mwh": mwh,
                "em": em,
            }
        )

    non_cbam_mwh_raw = facility_mwh_raw - cbam_mwh_raw
    non_cbam_em_raw = facility_em_raw - cbam_em_raw
    if non_cbam_mwh_raw < ZERO or non_cbam_em_raw < ZERO:
        raise BusinessRuleError(
            "Stage 1 attribution is unbalanced.",
            details=[{"code": "UNBALANCED_STAGE1"}],
        )

    group_list = [(pid, g["qty"]) for pid, g in ctx["groups"].items()]
    elec_pool_final, elec_product_rows = allocate_pool_with_largest_remainder(
        pool_raw=cbam_mwh_raw, groups=group_list
    )
    em_pool_final, em_product_rows = allocate_pool_with_largest_remainder(
        pool_raw=cbam_em_raw, groups=group_list
    )
    if (
        elec_pool_final - sum((r.final_allocated for r in elec_product_rows), ZERO) != ZERO
        or em_pool_final - sum((r.final_allocated for r in em_product_rows), ZERO) != ZERO
    ):
        raise BusinessRuleError(
            "Allocation balance is not exact.",
            details=[{"code": "UNBALANCED"}],
        )

    result_id = uuid.uuid4()
    facility_mwh_q = quantize_result(facility_mwh_raw)
    facility_em_q = quantize_result(facility_em_raw)
    non_cbam_mwh_q = facility_mwh_q - elec_pool_final
    non_cbam_em_q = facility_em_q - em_pool_final
    if non_cbam_mwh_q < ZERO or non_cbam_em_q < ZERO:
        raise BusinessRuleError(
            "Quantized facility/CBAM totals are inconsistent.",
            details=[{"code": "UNBALANCED"}],
        )

    result = CbamIndirectEmissionsAllocationResult(
        id=result_id,
        organization_id=organization_id,
        reporting_period_binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE,
        methodology_version=METHODOLOGY_VERSION,
        workbook_filename=WORKBOOK_FILENAME,
        workbook_sha256=WORKBOOK_SHA256,
        workbook_formula_refs=WORKBOOK_FORMULA_REFS,
        client_request_id=payload.client_request_id,
        request_fingerprint=fingerprint,
        status=EXECUTION_STATUS_COMPLETED,
        balance_status=BALANCE_BALANCED,
        facility_electricity_mwh_raw=facility_mwh_raw,
        cbam_electricity_mwh_raw=cbam_mwh_raw,
        non_cbam_electricity_mwh_raw=non_cbam_mwh_raw,
        facility_electricity_mwh=facility_mwh_q,
        cbam_electricity_mwh=elec_pool_final,
        non_cbam_electricity_mwh=non_cbam_mwh_q,
        allocated_electricity_mwh=elec_pool_final,
        remaining_electricity_mwh=ZERO,
        facility_indirect_emissions_tco2e_raw=facility_em_raw,
        cbam_indirect_emissions_tco2e_raw=cbam_em_raw,
        non_cbam_indirect_emissions_tco2e_raw=non_cbam_em_raw,
        facility_indirect_emissions_tco2e=facility_em_q,
        cbam_indirect_emissions_tco2e=em_pool_final,
        non_cbam_indirect_emissions_tco2e=non_cbam_em_q,
        allocated_indirect_emissions_tco2e=em_pool_final,
        remaining_indirect_emissions_tco2e=ZERO,
        exported_electricity_mwh=exported_total if has_exported else None,
        electricity_unit=RESULT_UNIT_ELECTRICITY,
        emissions_unit=RESULT_UNIT_EMISSIONS,
        source_result_count=len(source_rows),
        month_count=len(ctx["expected_months"]),
        participating_production_record_count=ctx["eligible_count"],
        product_profile_group_count=len(ctx["groups"]),
        totals_by_month_json=dict(sorted(totals_by_month.items())),
        created_by_user_id=user.id,
    )
    try:
        db.add(result)
        db.flush()

        for month, row in sorted(ctx["basis_rows"].items(), key=lambda t: t[0]):
            if month not in ctx["month_shares"]:
                continue
            assert row.total_production_quantity is not None and row.cbam_quantity is not None
            d_t = to_tonnes(row.total_production_quantity, row.quantity_unit)
            e_t = to_tonnes(row.cbam_quantity, row.quantity_unit)
            db.add(
                CbamIeaMonthlyBasisSnapshot(
                    id=uuid.uuid4(),
                    result_id=result_id,
                    organization_id=organization_id,
                    reporting_period_binding_id=binding_id,
                    basis_record_id=row.id,
                    basis_row_version=row.row_version,
                    month_start=month,
                    total_production_quantity=row.total_production_quantity,
                    cbam_quantity=row.cbam_quantity,
                    quantity_unit=row.quantity_unit,
                    normalized_total_production_tonnes=d_t,
                    normalized_cbam_quantity_tonnes=e_t,
                    monthly_share_raw=ctx["month_shares"][month],
                )
            )

        for s in source_rows:
            activity = s["activity"]
            pe = s["result"]
            db.add(
                CbamIeaSourceSnapshot(
                    id=uuid.uuid4(),
                    result_id=result_id,
                    organization_id=organization_id,
                    reporting_period_binding_id=binding_id,
                    source_result_id=pe.id,
                    source_run_id=pe.calculation_run_id,
                    activity_record_id=activity.id,
                    activity_date=activity.activity_date,
                    month_start=s["month"],
                    activity_quantity=pe.activity_quantity,
                    activity_unit=pe.activity_unit,
                    electricity_mwh=pe.electricity_mwh,
                    factor_source_mode=pe.factor_source_mode,
                    factor_value=pe.factor_value,
                    factor_unit=pe.factor_unit,
                    factor_tco2e_per_mwh=pe.factor_tco2e_per_mwh,
                    factor_source_name=pe.factor_source_name,
                    factor_source_document=pe.factor_source_document,
                    factor_dataset_version=pe.factor_dataset_version,
                    factor_reference_description=pe.factor_reference_description,
                    factor_effective_date=pe.factor_effective_date,
                    factor_valid_from=pe.factor_valid_from,
                    factor_valid_until=pe.factor_valid_until,
                    facility_electricity_mwh=s["mwh"].facility,
                    facility_indirect_emissions_tco2e=s["em"].facility,
                    monthly_share_raw=s["share"],
                    cbam_electricity_mwh=s["mwh"].cbam,
                    cbam_indirect_emissions_tco2e=s["em"].cbam,
                    non_cbam_electricity_mwh=s["mwh"].non_cbam,
                    non_cbam_indirect_emissions_tco2e=s["em"].non_cbam,
                    exported_electricity_quantity=pe.exported_electricity_quantity,
                    exported_electricity_unit=pe.exported_electricity_unit,
                    exported_electricity_mwh=pe.exported_electricity_mwh,
                )
            )

        denom = ctx["denom"]
        elec_by_id = {r.group_id: r for r in elec_product_rows}
        em_by_id = {r.group_id: r for r in em_product_rows}
        for profile_id, g in ctx["groups"].items():
            erow = elec_by_id[profile_id]
            emrow = em_by_id[profile_id]
            profile = g["profile"]
            db.add(
                CbamIeaProductAllocation(
                    id=uuid.uuid4(),
                    result_id=result_id,
                    organization_id=organization_id,
                    reporting_period_binding_id=binding_id,
                    product_id=profile.product_id,
                    product_profile_version_id=profile.id,
                    profile_version=profile.version,
                    cn_normalized_code=profile.cn_normalized_code,
                    cn_display_code=profile.cn_display_code,
                    product_name=profile.product_name,
                    production_record_ids=g["records"],
                    production_quantity_snapshots=g["snapshots"],
                    normalized_quantity_tonnes=g["qty"],
                    denominator_tonnes=denom,
                    raw_share=erow.share,
                    raw_allocated_electricity_mwh=erow.raw_allocated,
                    final_allocated_electricity_mwh=erow.final_allocated,
                    electricity_rounding_adjustment=erow.rounding_adjustment,
                    raw_allocated_indirect_emissions_tco2e=emrow.raw_allocated,
                    final_allocated_indirect_emissions_tco2e=emrow.final_allocated,
                    emissions_rounding_adjustment=emrow.rounding_adjustment,
                    electricity_unit=RESULT_UNIT_ELECTRICITY,
                    emissions_unit=RESULT_UNIT_EMISSIONS,
                )
            )

        _set_current_pointer(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            result_id=result_id,
        )
        write_audit_log(
            db,
            action="cbam.indirect_emissions_allocation.executed",
            actor_user_id=user.id,
            organization_id=organization_id,
            entity_type="cbam_indirect_emissions_allocation_results",
            entity_id=str(result_id),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={"clientRequestId": str(payload.client_request_id)},
        )
        db.commit()
        db.refresh(result)
        return _execution_response(result, idempotent_replay=False)
    except IntegrityError:
        db.rollback()
        winner = _find_by_client_request(
            db,
            organization_id=organization_id,
            binding_id=binding_id,
            client_request_id=payload.client_request_id,
        )
        if winner is None:
            raise ConflictError(
                "Indirect-emissions allocation persistence conflict.",
                details=[{"code": "ALLOCATION_RESULT_CONFLICT"}],
            ) from None
        if winner.request_fingerprint != fingerprint:
            raise ConflictError(
                "This client request id was already used with different inputs.",
                details=[{"code": "IDEMPOTENCY_KEY_REUSED"}],
            ) from None
        return _execution_response(winner, idempotent_replay=True)


def list_indirect_emissions_allocation_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[IndirectEmissionsAllocationResultSummary]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamIndirectEmissionsAllocationResult).where(
        CbamIndirectEmissionsAllocationResult.organization_id == organization_id,
        CbamIndirectEmissionsAllocationResult.reporting_period_binding_id == binding_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamIndirectEmissionsAllocationResult.created_at.desc(),
                CbamIndirectEmissionsAllocationResult.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    current_id = pointer.current_result_id if pointer else None
    items: list[IndirectEmissionsAllocationResultSummary] = []
    for row in rows:
        is_current = row.id == current_id
        stale_codes = (
            compute_allocation_stale_reasons(db, user, organization_id, binding_id, row)
            if is_current
            else []
        )
        items.append(
            IndirectEmissionsAllocationResultSummary(
                result_id=row.id,
                run_id=row.id,
                methodology_code=row.methodology_code,
                methodology_version=row.methodology_version,
                status=row.status,
                balance_status=row.balance_status,
                is_current=is_current,
                is_stale=bool(stale_codes),
                stale_reason_codes=stale_codes,
                facility_electricity_mwh=row.facility_electricity_mwh,
                cbam_electricity_mwh=row.cbam_electricity_mwh,
                non_cbam_electricity_mwh=row.non_cbam_electricity_mwh,
                allocated_electricity_mwh=row.allocated_electricity_mwh,
                remaining_electricity_mwh=row.remaining_electricity_mwh,
                facility_indirect_emissions_tco2e=row.facility_indirect_emissions_tco2e,
                cbam_indirect_emissions_tco2e=row.cbam_indirect_emissions_tco2e,
                allocated_indirect_emissions_tco2e=row.allocated_indirect_emissions_tco2e,
                remaining_indirect_emissions_tco2e=row.remaining_indirect_emissions_tco2e,
                exported_electricity_mwh=row.exported_electricity_mwh,
                electricity_unit=row.electricity_unit,
                emissions_unit=row.emissions_unit,
                created_at=row.created_at,
            )
        )
    return paginate(items, page=page, page_size=page_size, total_items=int(total))


def get_indirect_emissions_allocation_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> IndirectEmissionsAllocationResultDetail:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    row = db.execute(
        select(CbamIndirectEmissionsAllocationResult).where(
            CbamIndirectEmissionsAllocationResult.id == result_id,
            CbamIndirectEmissionsAllocationResult.organization_id == organization_id,
            CbamIndirectEmissionsAllocationResult.reporting_period_binding_id == binding_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Indirect-emissions allocation result not found.")

    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    is_current = pointer is not None and pointer.current_result_id == row.id
    stale_codes = (
        compute_allocation_stale_reasons(db, user, organization_id, binding_id, row)
        if is_current
        else []
    )

    monthly = [
        {
            "monthStart": b.month_start.isoformat(),
            "basisRecordId": str(b.basis_record_id),
            "basisRowVersion": b.basis_row_version,
            "totalProductionQuantity": str(b.total_production_quantity),
            "cbamQuantity": str(b.cbam_quantity),
            "quantityUnit": b.quantity_unit,
            "normalizedTotalProductionTonnes": str(b.normalized_total_production_tonnes),
            "normalizedCbamQuantityTonnes": str(b.normalized_cbam_quantity_tonnes),
            "monthlyShareRaw": str(b.monthly_share_raw),
        }
        for b in db.execute(
            select(CbamIeaMonthlyBasisSnapshot)
            .where(CbamIeaMonthlyBasisSnapshot.result_id == row.id)
            .order_by(CbamIeaMonthlyBasisSnapshot.month_start)
        ).scalars()
    ]
    sources = [
        {
            "sourceResultId": str(s.source_result_id),
            "activityRecordId": str(s.activity_record_id),
            "activityDate": s.activity_date.isoformat(),
            "monthStart": s.month_start.isoformat(),
            "activityQuantity": str(s.activity_quantity),
            "activityUnit": s.activity_unit,
            "electricityMwh": str(s.electricity_mwh),
            "factorSourceMode": s.factor_source_mode,
            "factorValue": str(s.factor_value),
            "factorUnit": s.factor_unit,
            "factorTco2ePerMwh": str(s.factor_tco2e_per_mwh),
            "factorSourceName": s.factor_source_name,
            "factorSourceDocument": s.factor_source_document,
            "factorDatasetVersion": s.factor_dataset_version,
            "factorReferenceDescription": s.factor_reference_description,
            "monthlyShareRaw": str(s.monthly_share_raw),
            "facilityElectricityMwh": str(s.facility_electricity_mwh),
            "cbamElectricityMwh": str(s.cbam_electricity_mwh),
            "nonCbamElectricityMwh": str(s.non_cbam_electricity_mwh),
            "facilityIndirectEmissionsTco2e": str(s.facility_indirect_emissions_tco2e),
            "cbamIndirectEmissionsTco2e": str(s.cbam_indirect_emissions_tco2e),
            "nonCbamIndirectEmissionsTco2e": str(s.non_cbam_indirect_emissions_tco2e),
            "exportedElectricityMwh": (
                str(s.exported_electricity_mwh) if s.exported_electricity_mwh is not None else None
            ),
        }
        for s in db.execute(
            select(CbamIeaSourceSnapshot)
            .where(CbamIeaSourceSnapshot.result_id == row.id)
            .order_by(CbamIeaSourceSnapshot.month_start, CbamIeaSourceSnapshot.source_result_id)
        ).scalars()
    ]
    products = [
        {
            "productId": str(p.product_id),
            "productProfileVersionId": str(p.product_profile_version_id),
            "profileVersion": p.profile_version,
            "cnNormalizedCode": p.cn_normalized_code,
            "cnDisplayCode": p.cn_display_code,
            "productName": p.product_name,
            "productionRecordIds": p.production_record_ids,
            "productionQuantitySnapshots": p.production_quantity_snapshots,
            "normalizedQuantityTonnes": str(p.normalized_quantity_tonnes),
            "denominatorTonnes": str(p.denominator_tonnes),
            "rawShare": str(p.raw_share),
            "rawAllocatedElectricityMwh": str(p.raw_allocated_electricity_mwh),
            "finalAllocatedElectricityMwh": str(p.final_allocated_electricity_mwh),
            "electricityRoundingAdjustment": str(p.electricity_rounding_adjustment),
            "rawAllocatedIndirectEmissionsTco2e": str(p.raw_allocated_indirect_emissions_tco2e),
            "finalAllocatedIndirectEmissionsTco2e": str(p.final_allocated_indirect_emissions_tco2e),
            "emissionsRoundingAdjustment": str(p.emissions_rounding_adjustment),
            "electricityUnit": p.electricity_unit,
            "emissionsUnit": p.emissions_unit,
        }
        for p in db.execute(
            select(CbamIeaProductAllocation)
            .where(CbamIeaProductAllocation.result_id == row.id)
            .order_by(CbamIeaProductAllocation.product_profile_version_id)
        ).scalars()
    ]

    return IndirectEmissionsAllocationResultDetail(
        result_id=row.id,
        run_id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        methodology_code=row.methodology_code,
        methodology_version=row.methodology_version,
        workbook_filename=row.workbook_filename,
        workbook_sha256=row.workbook_sha256,
        workbook_formula_refs=row.workbook_formula_refs,
        client_request_id=row.client_request_id,
        request_fingerprint=row.request_fingerprint,
        status=row.status,
        balance_status=row.balance_status,
        is_current=is_current,
        is_stale=bool(stale_codes),
        stale_reason_codes=stale_codes,
        facility_electricity_mwh_raw=row.facility_electricity_mwh_raw,
        cbam_electricity_mwh_raw=row.cbam_electricity_mwh_raw,
        non_cbam_electricity_mwh_raw=row.non_cbam_electricity_mwh_raw,
        facility_electricity_mwh=row.facility_electricity_mwh,
        cbam_electricity_mwh=row.cbam_electricity_mwh,
        non_cbam_electricity_mwh=row.non_cbam_electricity_mwh,
        allocated_electricity_mwh=row.allocated_electricity_mwh,
        remaining_electricity_mwh=row.remaining_electricity_mwh,
        facility_indirect_emissions_tco2e_raw=row.facility_indirect_emissions_tco2e_raw,
        cbam_indirect_emissions_tco2e_raw=row.cbam_indirect_emissions_tco2e_raw,
        non_cbam_indirect_emissions_tco2e_raw=row.non_cbam_indirect_emissions_tco2e_raw,
        facility_indirect_emissions_tco2e=row.facility_indirect_emissions_tco2e,
        cbam_indirect_emissions_tco2e=row.cbam_indirect_emissions_tco2e,
        non_cbam_indirect_emissions_tco2e=row.non_cbam_indirect_emissions_tco2e,
        allocated_indirect_emissions_tco2e=row.allocated_indirect_emissions_tco2e,
        remaining_indirect_emissions_tco2e=row.remaining_indirect_emissions_tco2e,
        exported_electricity_mwh=row.exported_electricity_mwh,
        electricity_unit=row.electricity_unit,
        emissions_unit=row.emissions_unit,
        source_result_count=row.source_result_count,
        month_count=row.month_count,
        participating_production_record_count=row.participating_production_record_count,
        product_profile_group_count=row.product_profile_group_count,
        totals_by_month=row.totals_by_month_json,
        monthly_basis=monthly,
        sources=sources,
        products=products,
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


def get_indirect_emissions_allocation_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> IndirectEmissionsAllocationPeriodSummary:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    if pointer is None:
        return IndirectEmissionsAllocationPeriodSummary(
            reporting_period_binding_id=binding_id,
            methodology_code=METHODOLOGY_CODE,
            current_result_id=None,
            current_is_stale=False,
            stale_reason_codes=[],
            facility_electricity_mwh=None,
            cbam_electricity_mwh=None,
            non_cbam_electricity_mwh=None,
            allocated_electricity_mwh=None,
            remaining_electricity_mwh=None,
            facility_indirect_emissions_tco2e=None,
            cbam_indirect_emissions_tco2e=None,
            allocated_indirect_emissions_tco2e=None,
            remaining_indirect_emissions_tco2e=None,
            exported_electricity_mwh=None,
            electricity_unit=RESULT_UNIT_ELECTRICITY,
            emissions_unit=RESULT_UNIT_EMISSIONS,
            balance_status=None,
            totals_by_month={},
            totals_by_product_profile=[],
        )
    detail = get_indirect_emissions_allocation_result(
        db, user, organization_id, binding_id, pointer.current_result_id
    )
    products = [
        {
            "productProfileVersionId": p["productProfileVersionId"],
            "productName": p["productName"],
            "finalAllocatedElectricityMwh": p["finalAllocatedElectricityMwh"],
            "finalAllocatedIndirectEmissionsTco2e": p["finalAllocatedIndirectEmissionsTco2e"],
        }
        for p in detail.products
    ]
    return IndirectEmissionsAllocationPeriodSummary(
        reporting_period_binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE,
        current_result_id=detail.result_id,
        current_is_stale=detail.is_stale,
        stale_reason_codes=detail.stale_reason_codes,
        facility_electricity_mwh=detail.facility_electricity_mwh,
        cbam_electricity_mwh=detail.cbam_electricity_mwh,
        non_cbam_electricity_mwh=detail.non_cbam_electricity_mwh,
        allocated_electricity_mwh=detail.allocated_electricity_mwh,
        remaining_electricity_mwh=detail.remaining_electricity_mwh,
        facility_indirect_emissions_tco2e=detail.facility_indirect_emissions_tco2e,
        cbam_indirect_emissions_tco2e=detail.cbam_indirect_emissions_tco2e,
        allocated_indirect_emissions_tco2e=detail.allocated_indirect_emissions_tco2e,
        remaining_indirect_emissions_tco2e=detail.remaining_indirect_emissions_tco2e,
        exported_electricity_mwh=detail.exported_electricity_mwh,
        electricity_unit=detail.electricity_unit,
        emissions_unit=detail.emissions_unit,
        balance_status=detail.balance_status,
        totals_by_month=detail.totals_by_month,
        totals_by_product_profile=products,
    )
