"""Stationary-combustion direct-emissions allocation execution.

Dedicated two-stage engine (monthly E/D attribution, then product quantity split).
Generic PRODUCTION_QUANTITY_RATIO is not used for Stage 1 monthly attribution.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
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
from ecotrace.modules.cbam.application.direct_emissions_allocation_constants import (
    BALANCE_BALANCED,
    EXECUTION_STATUS_COMPLETED,
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    RESULT_UNIT_TCO2,
    WORKBOOK_FILENAME,
    WORKBOOK_FORMULA_REFS,
    WORKBOOK_GAS,
    WORKBOOK_GWP,
    WORKBOOK_GWP_FACTOR,
    WORKBOOK_REPORTING_UNIT,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_idempotency import (
    build_direct_emissions_allocation_fingerprint,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_math import (
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
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    get_current_result_ids_for_binding,
    is_stationary_combustion_result_stale,
)
from ecotrace.modules.cbam.application.stationary_combustion_eligibility import (
    is_eligible_stationary_combustion_activity,
)
from ecotrace.modules.cbam.application.stationary_combustion_summary_service import (
    READINESS_READY,
    get_stationary_combustion_period_summary,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamDeaMonthlyBasisSnapshot,
    CbamDeaProductAllocation,
    CbamDeaSourceSnapshot,
    CbamDirectEmissionsAllocationCurrent,
    CbamDirectEmissionsAllocationResult,
    CbamMonthlyProductionBasis,
    CbamProductionRecord,
    CbamProductProfileVersion,
    CbamReportingPeriodBinding,
    CbamStationaryCombustionFuel,
    CbamStationaryCombustionResult,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

ReadinessStatus = Literal['READY', 'NOT_READY']


class DirectEmissionsAllocationExecuteRequest(CamelModel):
    client_request_id: uuid.UUID


class DirectEmissionsAllocationExecutionResponse(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    status: str
    methodology_code: str
    methodology_version: str
    balance_status: str
    facility_fossil_co2_tonnes: Decimal
    cbam_fossil_co2_tonnes: Decimal
    non_cbam_fossil_co2_tonnes: Decimal
    allocated_fossil_co2_tonnes: Decimal
    remaining_fossil_co2_tonnes: Decimal
    result_unit: str
    workbook_reporting_unit: str
    client_request_id: uuid.UUID
    idempotent_replay: bool
    created_at: datetime


class DirectEmissionsAllocationReadiness(CamelModel):
    status: ReadinessStatus
    allocation_ready: bool
    blocking_issue_codes: list[str]
    stationary_combustion_status: str
    monthly_production_basis_status: str
    production_profile_status: str
    production_reconciliation_status: str
    source_result_count: int
    month_count: int
    fuel_count: int
    participating_production_record_count: int
    product_profile_group_count: int
    current_allocation_id: uuid.UUID | None
    current_allocation_stale: bool
    stale_reason_codes: list[str]


class DirectEmissionsAllocationResultSummary(CamelModel):
    result_id: uuid.UUID
    run_id: uuid.UUID
    methodology_code: str
    methodology_version: str
    status: str
    balance_status: str
    is_current: bool
    is_stale: bool
    stale_reason_codes: list[str]
    facility_fossil_co2_tonnes: Decimal
    cbam_fossil_co2_tonnes: Decimal
    non_cbam_fossil_co2_tonnes: Decimal
    allocated_fossil_co2_tonnes: Decimal
    remaining_fossil_co2_tonnes: Decimal
    result_unit: str
    workbook_reporting_unit: str
    created_at: datetime


class DirectEmissionsAllocationPeriodSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    methodology_code: str
    current_result_id: uuid.UUID | None
    current_is_stale: bool
    stale_reason_codes: list[str]
    facility_fossil_co2_tonnes: Decimal | None
    cbam_fossil_co2_tonnes: Decimal | None
    non_cbam_fossil_co2_tonnes: Decimal | None
    allocated_fossil_co2_tonnes: Decimal | None
    remaining_fossil_co2_tonnes: Decimal | None
    result_unit: str
    workbook_reporting_unit: str
    balance_status: str | None
    totals_by_month: dict[str, Any]
    totals_by_fuel: dict[str, Any]
    totals_by_product_profile: list[dict[str, Any]]


class DirectEmissionsAllocationResultDetail(CamelModel):
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
    facility_fossil_co2_tonnes_raw: Decimal
    cbam_fossil_co2_tonnes_raw: Decimal
    non_cbam_fossil_co2_tonnes_raw: Decimal
    facility_fossil_co2_tonnes: Decimal
    cbam_fossil_co2_tonnes: Decimal
    non_cbam_fossil_co2_tonnes: Decimal
    allocated_fossil_co2_tonnes: Decimal
    remaining_fossil_co2_tonnes: Decimal
    result_unit: str
    workbook_reporting_unit: str
    workbook_gas: str
    workbook_gwp: str
    workbook_gwp_factor: str
    totals_by_month: dict[str, Any]
    totals_by_fuel: dict[str, Any]
    monthly_basis: list[dict[str, Any]]
    source_calculations: list[dict[str, Any]]
    product_allocations: list[dict[str, Any]]
    created_at: datetime
    created_by_user_id: uuid.UUID | None


def _period(
    db: Session, organization_id: uuid.UUID, binding: CbamReportingPeriodBinding
) -> Any:
    return require_reporting_period_in_organization(
        db, organization_id=organization_id, reporting_period_id=binding.reporting_period_id
    )


def _active_fuels_by_code(db: Session) -> dict[str, CbamStationaryCombustionFuel]:
    rows = db.execute(
        select(CbamStationaryCombustionFuel).where(
            CbamStationaryCombustionFuel.status == 'ACTIVE'
        )
    ).scalars()
    return {f.code: f for f in rows}


def _current_pointer(
    db: Session, *, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> CbamDirectEmissionsAllocationCurrent | None:
    return db.execute(
        select(CbamDirectEmissionsAllocationCurrent).where(
            CbamDirectEmissionsAllocationCurrent.organization_id == organization_id,
            CbamDirectEmissionsAllocationCurrent.reporting_period_binding_id == binding_id,
            CbamDirectEmissionsAllocationCurrent.methodology_code == METHODOLOGY_CODE,
        )
    ).scalar_one_or_none()


def _set_current_pointer(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> None:
    now = datetime.now(UTC)
    stmt = (
        pg_insert(CbamDirectEmissionsAllocationCurrent)
        .values(
            id=uuid.uuid4(),
            organization_id=organization_id,
            reporting_period_binding_id=binding_id,
            methodology_code=METHODOLOGY_CODE,
            current_result_id=result_id,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_update(
            constraint='uq_cbam_dea_current_org_binding_method',
            set_={'current_result_id': result_id, 'updated_at': now},
        )
    )
    db.execute(stmt)


def _find_by_client_request(
    db: Session,
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    client_request_id: uuid.UUID,
) -> CbamDirectEmissionsAllocationResult | None:
    return db.execute(
        select(CbamDirectEmissionsAllocationResult).where(
            CbamDirectEmissionsAllocationResult.organization_id == organization_id,
            CbamDirectEmissionsAllocationResult.reporting_period_binding_id == binding_id,
            CbamDirectEmissionsAllocationResult.client_request_id == client_request_id,
        )
    ).scalar_one_or_none()


def _dedupe_codes(codes: list[str]) -> list[str]:
    out: list[str] = []
    for c in codes:
        if c not in out:
            out.append(c)
    return out


def _resolve_context(
    db: Session, user: User, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> dict[str, Any]:
    binding = get_binding_for_org(db, organization_id, binding_id)
    period = _period(db, organization_id, binding)
    expected_months = iter_expected_months(period.start_date, period.end_date)
    blocking: list[str] = []

    sc_summary = get_stationary_combustion_period_summary(
        db, user, organization_id, binding_id
    )
    sc_status = sc_summary.readiness_status
    if sc_status != READINESS_READY:
        if sc_summary.stale_result_count > 0 or sc_status == 'STALE':
            blocking.append('DIRECT_EMISSIONS_STALE')
        else:
            blocking.append('DIRECT_EMISSIONS_NOT_READY')

    pointer_map = get_current_result_ids_for_binding(
        db, organization_id=organization_id, binding_id=binding_id
    )
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
    results: dict[uuid.UUID, CbamStationaryCombustionResult] = {}
    if result_ids:
        results = {
            r.id: r
            for r in db.execute(
                select(CbamStationaryCombustionResult).where(
                    CbamStationaryCombustionResult.id.in_(result_ids)
                )
            ).scalars()
        }

    fuels_by_code = _active_fuels_by_code(db)
    sources: list[tuple[CbamActivityRecord, CbamStationaryCombustionResult, date]] = []
    fuel_codes: set[str] = set()
    for activity_id, result_id in pointer_map.items():
        activity = activities.get(activity_id)
        result = results.get(result_id)
        if activity is None or result is None:
            blocking.append('DIRECT_EMISSIONS_NOT_READY')
            continue
        if activity.status != 'active' or not is_eligible_stationary_combustion_activity(
            activity, fuels_by_code
        ):
            continue
        if activity.activity_date is None:
            blocking.append('COMBUSTION_ACTIVITY_DATE_REQUIRED')
            continue
        month = canonical_month_start(activity.activity_date)
        if month not in expected_months:
            blocking.append('COMBUSTION_MONTH_NOT_COVERED')
            continue
        if is_stationary_combustion_result_stale(activity, result):
            blocking.append('DIRECT_EMISSIONS_STALE')
            continue
        sources.append((activity, result, month))
        fuel_codes.add(result.fuel_code)

    if sc_status == READINESS_READY and not sources:
        blocking.append('DIRECT_EMISSIONS_NOT_READY')

    mb_summary = get_monthly_production_basis_summary(db, user, organization_id, binding_id)
    mb_status = mb_summary.status
    if not mb_summary.allocation_basis_ready:
        blocking.append('MONTHLY_PRODUCTION_BASIS_NOT_READY')
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
            blocking.append('MONTHLY_PRODUCTION_BASIS_NOT_READY')
            continue
        try:
            d_t = to_tonnes(row.total_production_quantity, row.quantity_unit)
            e_t = to_tonnes(row.cbam_quantity, row.quantity_unit)
            month_shares[month] = monthly_cbam_share(
                total_production_tonnes=d_t, cbam_quantity_tonnes=e_t
            )
        except ValueError as exc:
            if str(exc) == 'TOTAL_PRODUCTION_MUST_BE_POSITIVE':
                blocking.append('TOTAL_PRODUCTION_MUST_BE_POSITIVE')
            else:
                blocking.append('MONTHLY_PRODUCTION_BASIS_NOT_READY')
        except Exception:
            blocking.append('MONTHLY_PRODUCTION_BASIS_NOT_READY')

    recon_status = 'EXACT_MATCH'
    for item in mb_summary.production_reconciliation:
        if item.reconciliation_status == 'MISMATCH':
            blocking.append('PRODUCTION_RECONCILIATION_MISMATCH')
            recon_status = 'MISMATCH'
        elif item.reconciliation_status == 'UNAVAILABLE':
            blocking.append('PRODUCTION_RECONCILIATION_UNAVAILABLE')
            if recon_status != 'MISMATCH':
                recon_status = 'UNAVAILABLE'

    prod_rows = list(
        db.execute(
            select(CbamProductionRecord).where(
                CbamProductionRecord.organization_id == organization_id,
                CbamProductionRecord.reporting_period_binding_id == binding_id,
                CbamProductionRecord.status == 'active',
            )
        ).scalars()
    )
    profile_ids = {
        p.product_profile_version_id
        for p in prod_rows
        if p.product_profile_version_id is not None
    }
    profiles: dict[uuid.UUID, CbamProductProfileVersion] = {}
    if profile_ids:
        profiles = {
            p.id: p
            for p in db.execute(
                select(CbamProductProfileVersion).where(
                    CbamProductProfileVersion.id.in_(profile_ids)
                )
            ).scalars()
        }

    eligible: list[tuple[CbamProductionRecord, CbamProductProfileVersion, Decimal]] = []
    profile_status = 'READY'
    for prod in prod_rows:
        if prod.production_date is None:
            blocking.append('PRODUCTION_DATE_REQUIRED')
            profile_status = 'NOT_READY'
            continue
        link_status, _codes, profile = compute_profile_link_state(db, prod)
        if link_status == 'MISSING':
            blocking.append('PRODUCTION_PROFILE_LINK_MISSING')
            profile_status = 'NOT_READY'
            continue
        if link_status == 'INVALID' or not is_allocation_eligible_link(link_status):
            blocking.append('PRODUCTION_PROFILE_LINK_INVALID')
            profile_status = 'NOT_READY'
            continue
        if profile is None:
            profile = profiles.get(prod.product_profile_version_id) if prod.product_profile_version_id else None
        if profile is None:
            blocking.append('PRODUCTION_PROFILE_LINK_MISSING')
            profile_status = 'NOT_READY'
            continue
        try:
            tonnes = to_tonnes(prod.quantity, prod.unit)
        except Exception:
            blocking.append('INCOMPATIBLE_PRODUCTION_UNIT')
            profile_status = 'NOT_READY'
            continue
        if tonnes <= 0:
            blocking.append('NO_ELIGIBLE_PRODUCTION')
            profile_status = 'NOT_READY'
            continue
        eligible.append((prod, profile, tonnes))

    groups: dict[uuid.UUID, dict[str, Any]] = {}
    for prod, profile, tonnes in eligible:
        g = groups.setdefault(
            profile.id,
            {
                'profile': profile,
                'product_id': profile.product_id,
                'qty': ZERO,
                'records': [],
                'snapshots': [],
            },
        )
        g['qty'] += tonnes
        g['records'].append(str(prod.id))
        g['snapshots'].append(
            {
                'productionRecordId': str(prod.id),
                'quantity': str(prod.quantity),
                'unit': prod.unit,
                'productionDate': (
                    prod.production_date.isoformat() if prod.production_date else None
                ),
                'normalizedTonnes': str(tonnes),
                'productProfileVersionId': str(profile.id),
            }
        )

    # Deterministic subordinate snapshot order (by production record id).
    for g in groups.values():
        paired = sorted(
            zip(g['records'], g['snapshots'], strict=True),
            key=lambda t: t[0],
        )
        g['records'] = [r for r, _ in paired]
        g['snapshots'] = [s for _, s in paired]

    if not groups:
        blocking.append('NO_ELIGIBLE_PRODUCTION')
        profile_status = 'NOT_READY'
    denom = sum((g['qty'] for g in groups.values()), ZERO)
    if groups and denom <= 0:
        blocking.append('ZERO_ALLOCATION_DENOMINATOR')

    blocking = _dedupe_codes(blocking)
    return {
        'binding': binding,
        'expected_months': expected_months,
        'blocking': blocking,
        'sc_status': sc_status,
        'mb_status': mb_status,
        'mb_summary': mb_summary,
        'recon_status': recon_status,
        'profile_status': profile_status,
        'sources': sources,
        'basis_rows': basis_rows,
        'month_shares': month_shares,
        'groups': groups,
        'denom': denom,
        'eligible_count': len(eligible),
        'fuel_count': len(fuel_codes),
    }


def compute_allocation_stale_reasons(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result: CbamDirectEmissionsAllocationResult,
) -> list[str]:
    """Compare live material identity to immutable snapshot (no live catalog recompute of values)."""
    reasons: list[str] = []
    if (
        result.methodology_code != METHODOLOGY_CODE
        or result.methodology_version != METHODOLOGY_VERSION
        or result.workbook_sha256 != WORKBOOK_SHA256
    ):
        reasons.append('METHODOLOGY_OR_WORKBOOK_CHANGED')

    ctx = _resolve_context(db, user, organization_id, binding_id)
    live_source_ids = {r.id for _, r, _ in ctx['sources']}
    snap_sources = list(
        db.execute(
            select(CbamDeaSourceSnapshot).where(CbamDeaSourceSnapshot.result_id == result.id)
        ).scalars()
    )
    snap_source_ids = {s.source_result_id for s in snap_sources}
    if live_source_ids != snap_source_ids:
        reasons.append('SOURCE_CURRENT_RESULT_CHANGED')

    pointer_map = get_current_result_ids_for_binding(
        db, organization_id=organization_id, binding_id=binding_id
    )
    for snap in snap_sources:
        if pointer_map.get(snap.activity_record_id) != snap.source_result_id:
            reasons.append('SOURCE_CURRENT_RESULT_CHANGED')
        activity = db.get(CbamActivityRecord, snap.activity_record_id)
        sc = db.get(CbamStationaryCombustionResult, snap.source_result_id)
        if activity is None or sc is None:
            reasons.append('SOURCE_CURRENT_RESULT_CHANGED')
        elif is_stationary_combustion_result_stale(activity, sc):
            reasons.append('DIRECT_EMISSIONS_STALE')
        elif (
            activity.quantity != snap.activity_quantity
            or activity.unit != snap.activity_unit
            or activity.activity_date != snap.activity_date
            or activity.activity_type != snap.fuel_code
        ):
            reasons.append('SOURCE_ACTIVITY_MATERIAL_CHANGED')

    snap_basis = list(
        db.execute(
            select(CbamDeaMonthlyBasisSnapshot).where(
                CbamDeaMonthlyBasisSnapshot.result_id == result.id
            )
        ).scalars()
    )
    live_basis = ctx['basis_rows']
    snap_basis_ids = {b.basis_record_id for b in snap_basis}
    live_basis_ids = {r.id for r in live_basis.values()}
    if snap_basis_ids != live_basis_ids:
        reasons.append('MONTHLY_PRODUCTION_BASIS_CHANGED')
    for sb in snap_basis:
        live = live_basis.get(sb.month_start)
        if live is None:
            reasons.append('MONTHLY_PRODUCTION_BASIS_CHANGED')
            continue
        if (
            live.row_version != sb.basis_row_version
            or live.total_production_quantity != sb.total_production_quantity
            or live.cbam_quantity != sb.cbam_quantity
            or live.quantity_unit != sb.quantity_unit
        ):
            reasons.append('MONTHLY_PRODUCTION_BASIS_CHANGED')

    snap_products = list(
        db.execute(
            select(CbamDeaProductAllocation).where(CbamDeaProductAllocation.result_id == result.id)
        ).scalars()
    )
    live_prod_ids: set[str] = set()
    for g in ctx['groups'].values():
        live_prod_ids.update(g['records'])
    snap_prod_ids: set[str] = set()
    for sp in snap_products:
        snap_prod_ids.update(str(x) for x in (sp.production_record_ids or []))
    if live_prod_ids != snap_prod_ids:
        reasons.append('PRODUCTION_SET_CHANGED')

    for sp in snap_products:
        for item in sp.production_quantity_snapshots or []:
            pid = uuid.UUID(item['productionRecordId'])
            prod = db.get(CbamProductionRecord, pid)
            if prod is None or prod.status != 'active':
                reasons.append('PRODUCTION_SET_CHANGED')
                continue
            snap_profile = item.get('productProfileVersionId')
            live_profile = (
                str(prod.product_profile_version_id)
                if prod.product_profile_version_id is not None
                else None
            )
            if (
                str(prod.quantity) != str(item.get('quantity'))
                or prod.unit != item.get('unit')
                or (
                    prod.production_date.isoformat()
                    if prod.production_date
                    else None
                )
                != item.get('productionDate')
                or live_profile != snap_profile
                or prod.product_profile_version_id != sp.product_profile_version_id
            ):
                reasons.append('PRODUCTION_MATERIAL_CHANGED')
            link_status, _codes2, _ = compute_profile_link_state(db, prod)
            if link_status == 'INVALID':
                reasons.append('PRODUCTION_PROFILE_LINK_INVALID')
            elif link_status == 'MISSING':
                reasons.append('PRODUCTION_PROFILE_LINK_MISSING')

    return _dedupe_codes(reasons)


def assert_monthly_basis_not_referenced(
    db: Session, *, organization_id: uuid.UUID, basis_record_id: uuid.UUID
) -> None:
    exists = db.execute(
        select(CbamDeaMonthlyBasisSnapshot.id).where(
            CbamDeaMonthlyBasisSnapshot.organization_id == organization_id,
            CbamDeaMonthlyBasisSnapshot.basis_record_id == basis_record_id,
        ).limit(1)
    ).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(
            'This monthly record is used by a completed allocation and cannot be deleted.',
            details=[{'code': 'MONTHLY_PRODUCTION_BASIS_REFERENCED_BY_ALLOCATION'}],
        )


def assert_production_record_not_referenced(
    db: Session, *, organization_id: uuid.UUID, production_record_id: uuid.UUID
) -> None:
    """Block archive/delete when a completed allocation snapshot references the record."""
    exists = db.execute(
        select(CbamDeaProductAllocation.id).where(
            CbamDeaProductAllocation.organization_id == organization_id,
            CbamDeaProductAllocation.production_record_ids.contains(
                [str(production_record_id)]
            ),
        ).limit(1)
    ).scalar_one_or_none()
    if exists is not None:
        raise ConflictError(
            'This production record is used by a completed allocation and cannot be archived.',
            details=[{'code': 'PRODUCTION_RECORD_REFERENCED_BY_ALLOCATION'}],
        )


def get_direct_emissions_allocation_readiness(
    db: Session, user: User, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> DirectEmissionsAllocationReadiness:
    require_cbam_view(db, user, organization_id)
    ctx = _resolve_context(db, user, organization_id, binding_id)
    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    stale_codes: list[str] = []
    current_id = pointer.current_result_id if pointer else None
    current_stale = False
    if pointer is not None:
        result = db.get(CbamDirectEmissionsAllocationResult, pointer.current_result_id)
        if result is not None:
            stale_codes = compute_allocation_stale_reasons(
                db, user, organization_id, binding_id, result
            )
            current_stale = bool(stale_codes)
    ready = len(ctx['blocking']) == 0
    return DirectEmissionsAllocationReadiness(
        status='READY' if ready else 'NOT_READY',
        allocation_ready=ready,
        blocking_issue_codes=ctx['blocking'],
        stationary_combustion_status=ctx['sc_status'],
        monthly_production_basis_status=ctx['mb_status'],
        production_profile_status=ctx['profile_status'],
        production_reconciliation_status=ctx['recon_status'],
        source_result_count=len(ctx['sources']),
        month_count=len(ctx['expected_months']),
        fuel_count=ctx['fuel_count'],
        participating_production_record_count=ctx['eligible_count'],
        product_profile_group_count=len(ctx['groups']),
        current_allocation_id=current_id,
        current_allocation_stale=current_stale,
        stale_reason_codes=stale_codes,
    )


def _execution_response(
    result: CbamDirectEmissionsAllocationResult, *, idempotent_replay: bool
) -> DirectEmissionsAllocationExecutionResponse:
    return DirectEmissionsAllocationExecutionResponse(
        result_id=result.id,
        run_id=result.id,
        status=result.status,
        methodology_code=result.methodology_code,
        methodology_version=result.methodology_version,
        balance_status=result.balance_status,
        facility_fossil_co2_tonnes=result.facility_fossil_co2_tonnes,
        cbam_fossil_co2_tonnes=result.cbam_fossil_co2_tonnes,
        non_cbam_fossil_co2_tonnes=result.non_cbam_fossil_co2_tonnes,
        allocated_fossil_co2_tonnes=result.allocated_fossil_co2_tonnes,
        remaining_fossil_co2_tonnes=result.remaining_fossil_co2_tonnes,
        result_unit=result.result_unit,
        workbook_reporting_unit=result.workbook_reporting_unit,
        client_request_id=result.client_request_id,
        idempotent_replay=idempotent_replay,
        created_at=result.created_at,
    )


def execute_direct_emissions_allocation(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: DirectEmissionsAllocationExecuteRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DirectEmissionsAllocationExecutionResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)

    ctx = _resolve_context(db, user, organization_id, binding_id)
    if ctx['blocking']:
        raise BusinessRuleError(
            'Direct-emissions allocation is not ready.',
            details=[{'code': c} for c in ctx['blocking']],
        )

    source_result_ids = [r.id for _, r, _ in ctx['sources']]
    source_material = [
        (r.id, r.fuel_code, r.activity_quantity, r.activity_unit) for _, r, _ in ctx['sources']
    ]
    monthly_basis_fp = []
    for month, row in sorted(ctx['basis_rows'].items(), key=lambda t: t[0]):
        if month not in ctx['month_shares']:
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
    for g in ctx['groups'].values():
        for snap in g['snapshots']:
            production_fp.append(
                (
                    uuid.UUID(snap['productionRecordId']),
                    Decimal(snap['quantity']),
                    snap['unit'],
                    snap['productionDate'] or '-',
                    str(g['profile'].id),
                )
            )

    fingerprint = build_direct_emissions_allocation_fingerprint(
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
                'This client request id was already used with different inputs.',
                details=[{'code': 'IDEMPOTENCY_KEY_REUSED'}],
            )
        return _execution_response(existing, idempotent_replay=True)

    # Stage 1
    facility_raw = ZERO
    cbam_raw = ZERO
    non_cbam_raw = ZERO
    source_rows: list[dict[str, Any]] = []
    totals_by_month: dict[str, Decimal] = defaultdict(lambda: ZERO)
    totals_by_fuel: dict[str, Decimal] = defaultdict(lambda: ZERO)

    for activity, result, month in ctx['sources']:
        share = ctx['month_shares'][month]
        mass_kg = attribute_measure(result.fuel_mass_kg, share)
        mass_gg = attribute_measure(result.fuel_mass_gg, share)
        energy = attribute_measure(result.energy_content_tj, share)
        co2_kg = attribute_measure(result.fossil_co2_kg, share)
        co2_t = attribute_measure(result.fossil_co2_tonnes, share)
        facility_raw += co2_t.facility
        cbam_raw += co2_t.cbam
        non_cbam_raw += co2_t.non_cbam
        totals_by_month[month.isoformat()] += co2_t.cbam
        totals_by_fuel[result.fuel_code] += co2_t.cbam
        source_rows.append(
            {
                'activity': activity,
                'result': result,
                'month': month,
                'share': share,
                'mass_kg': mass_kg,
                'mass_gg': mass_gg,
                'energy': energy,
                'co2_kg': co2_kg,
                'co2_t': co2_t,
            }
        )

    # Aggregate invariant: derive remainder so facility = cbam + non_cbam exactly.
    non_cbam_raw = facility_raw - cbam_raw
    if non_cbam_raw < ZERO:
        raise BusinessRuleError(
            'Stage 1 attribution is unbalanced.',
            details=[{'code': 'UNBALANCED_STAGE1'}],
        )

    group_list = [(pid, g['qty']) for pid, g in ctx['groups'].items()]
    pool_final, product_rows = allocate_pool_with_largest_remainder(
        pool_raw=cbam_raw, groups=group_list
    )
    allocated_final = sum((r.final_allocated for r in product_rows), ZERO)
    remaining = pool_final - allocated_final
    if remaining != ZERO:
        raise BusinessRuleError(
            'Allocation balance is not exact.',
            details=[{'code': 'UNBALANCED'}],
        )
    balance_status = BALANCE_BALANCED

    result_id = uuid.uuid4()
    facility_q = quantize_result(facility_raw)
    cbam_q = pool_final
    non_cbam_q = facility_q - cbam_q
    if non_cbam_q < ZERO:
        raise BusinessRuleError(
            'Quantized facility/CBAM totals are inconsistent.',
            details=[{'code': 'UNBALANCED'}],
        )

    result = CbamDirectEmissionsAllocationResult(
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
        balance_status=balance_status,
        facility_fossil_co2_tonnes_raw=facility_raw,
        cbam_fossil_co2_tonnes_raw=cbam_raw,
        non_cbam_fossil_co2_tonnes_raw=non_cbam_raw,
        facility_fossil_co2_tonnes=facility_q,
        cbam_fossil_co2_tonnes=cbam_q,
        non_cbam_fossil_co2_tonnes=non_cbam_q,
        allocated_fossil_co2_tonnes=allocated_final,
        remaining_fossil_co2_tonnes=ZERO,
        result_unit=RESULT_UNIT_TCO2,
        workbook_reporting_unit=WORKBOOK_REPORTING_UNIT,
        workbook_gas=WORKBOOK_GAS,
        workbook_gwp=WORKBOOK_GWP,
        workbook_gwp_factor=WORKBOOK_GWP_FACTOR,
        source_result_count=len(source_rows),
        month_count=len(ctx['expected_months']),
        fuel_count=ctx['fuel_count'],
        participating_production_record_count=ctx['eligible_count'],
        product_profile_group_count=len(ctx['groups']),
        totals_by_month_json={k: str(v) for k, v in sorted(totals_by_month.items())},
        totals_by_fuel_json={k: str(v) for k, v in sorted(totals_by_fuel.items())},
        created_by_user_id=user.id,
    )
    try:
        db.add(result)
        db.flush()

        for month, row in sorted(ctx['basis_rows'].items(), key=lambda t: t[0]):
            if month not in ctx['month_shares']:
                continue
            assert row.total_production_quantity is not None and row.cbam_quantity is not None
            d_t = to_tonnes(row.total_production_quantity, row.quantity_unit)
            e_t = to_tonnes(row.cbam_quantity, row.quantity_unit)
            db.add(
                CbamDeaMonthlyBasisSnapshot(
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
                    monthly_share_raw=ctx['month_shares'][month],
                )
            )

        for s in source_rows:
            activity = s['activity']
            sc = s['result']
            db.add(
                CbamDeaSourceSnapshot(
                    id=uuid.uuid4(),
                    result_id=result_id,
                    organization_id=organization_id,
                    reporting_period_binding_id=binding_id,
                    source_result_id=sc.id,
                    source_run_id=sc.calculation_run_id,
                    activity_record_id=activity.id,
                    activity_date=activity.activity_date,
                    month_start=s['month'],
                    fuel_code=sc.fuel_code,
                    fuel_name=sc.fuel_name,
                    dataset_code=sc.dataset_code,
                    dataset_version=sc.dataset_version,
                    activity_quantity=sc.activity_quantity,
                    activity_unit=sc.activity_unit,
                    facility_fuel_mass_kg=s['mass_kg'].facility,
                    facility_fuel_mass_gg=s['mass_gg'].facility,
                    facility_energy_content_tj=s['energy'].facility,
                    facility_fossil_co2_kg=s['co2_kg'].facility,
                    facility_fossil_co2_tonnes=s['co2_t'].facility,
                    facility_result_value=sc.result_value,
                    monthly_share_raw=s['share'],
                    cbam_fuel_mass_kg=s['mass_kg'].cbam,
                    cbam_fuel_mass_gg=s['mass_gg'].cbam,
                    cbam_energy_content_tj=s['energy'].cbam,
                    cbam_fossil_co2_kg=s['co2_kg'].cbam,
                    cbam_fossil_co2_tonnes=s['co2_t'].cbam,
                    non_cbam_fuel_mass_kg=s['mass_kg'].non_cbam,
                    non_cbam_fuel_mass_gg=s['mass_gg'].non_cbam,
                    non_cbam_energy_content_tj=s['energy'].non_cbam,
                    non_cbam_fossil_co2_kg=s['co2_kg'].non_cbam,
                    non_cbam_fossil_co2_tonnes=s['co2_t'].non_cbam,
                )
            )

        denom = ctx['denom']
        by_id = {r.group_id: r for r in product_rows}
        for profile_id, g in ctx['groups'].items():
            row = by_id[profile_id]
            profile = g['profile']
            db.add(
                CbamDeaProductAllocation(
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
                    production_record_ids=g['records'],
                    production_quantity_snapshots=g['snapshots'],
                    normalized_quantity_tonnes=g['qty'],
                    denominator_tonnes=denom,
                    raw_share=row.share,
                    raw_allocated_fossil_co2_tonnes=row.raw_allocated,
                    final_allocated_fossil_co2_tonnes=row.final_allocated,
                    rounding_adjustment=row.rounding_adjustment,
                    result_unit=RESULT_UNIT_TCO2,
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
            action='cbam.direct_emissions_allocation.executed',
            actor_user_id=user.id,
            organization_id=organization_id,
            entity_type='cbam_direct_emissions_allocation_results',
            entity_id=str(result_id),
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata={'clientRequestId': str(payload.client_request_id)},
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
                'Direct-emissions allocation persistence conflict.',
                details=[{'code': 'ALLOCATION_RESULT_CONFLICT'}],
            ) from None
        if winner.request_fingerprint != fingerprint:
            raise ConflictError(
                'This client request id was already used with different inputs.',
                details=[{'code': 'IDEMPOTENCY_KEY_REUSED'}],
            ) from None
        return _execution_response(winner, idempotent_replay=True)


def list_direct_emissions_allocation_results(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[DirectEmissionsAllocationResultSummary]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamDirectEmissionsAllocationResult).where(
        CbamDirectEmissionsAllocationResult.organization_id == organization_id,
        CbamDirectEmissionsAllocationResult.reporting_period_binding_id == binding_id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamDirectEmissionsAllocationResult.created_at.desc(),
                CbamDirectEmissionsAllocationResult.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    current_id = pointer.current_result_id if pointer else None
    items: list[DirectEmissionsAllocationResultSummary] = []
    for row in rows:
        is_current = row.id == current_id
        stale_codes = (
            compute_allocation_stale_reasons(db, user, organization_id, binding_id, row)
            if is_current
            else []
        )
        items.append(
            DirectEmissionsAllocationResultSummary(
                result_id=row.id,
                run_id=row.id,
                methodology_code=row.methodology_code,
                methodology_version=row.methodology_version,
                status=row.status,
                balance_status=row.balance_status,
                is_current=is_current,
                is_stale=bool(stale_codes),
                stale_reason_codes=stale_codes,
                facility_fossil_co2_tonnes=row.facility_fossil_co2_tonnes,
                cbam_fossil_co2_tonnes=row.cbam_fossil_co2_tonnes,
                non_cbam_fossil_co2_tonnes=row.non_cbam_fossil_co2_tonnes,
                allocated_fossil_co2_tonnes=row.allocated_fossil_co2_tonnes,
                remaining_fossil_co2_tonnes=row.remaining_fossil_co2_tonnes,
                result_unit=row.result_unit,
                workbook_reporting_unit=row.workbook_reporting_unit,
                created_at=row.created_at,
            )
        )
    return paginate(items, page=page, page_size=page_size, total_items=int(total))


def get_direct_emissions_allocation_result(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    result_id: uuid.UUID,
) -> DirectEmissionsAllocationResultDetail:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    row = db.execute(
        select(CbamDirectEmissionsAllocationResult).where(
            CbamDirectEmissionsAllocationResult.id == result_id,
            CbamDirectEmissionsAllocationResult.organization_id == organization_id,
            CbamDirectEmissionsAllocationResult.reporting_period_binding_id == binding_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError('Direct-emissions allocation result not found.')

    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    is_current = pointer is not None and pointer.current_result_id == row.id
    stale_codes = (
        compute_allocation_stale_reasons(db, user, organization_id, binding_id, row)
        if is_current
        else []
    )

    monthly = [
        {
            'basisRecordId': str(m.basis_record_id),
            'basisRowVersion': m.basis_row_version,
            'monthStart': m.month_start.isoformat(),
            'totalProductionQuantity': str(m.total_production_quantity),
            'cbamQuantity': str(m.cbam_quantity),
            'quantityUnit': m.quantity_unit,
            'normalizedTotalProductionTonnes': str(m.normalized_total_production_tonnes),
            'normalizedCbamQuantityTonnes': str(m.normalized_cbam_quantity_tonnes),
            'monthlyShareRaw': str(m.monthly_share_raw),
        }
        for m in db.execute(
            select(CbamDeaMonthlyBasisSnapshot)
            .where(CbamDeaMonthlyBasisSnapshot.result_id == row.id)
            .order_by(CbamDeaMonthlyBasisSnapshot.month_start.asc())
        ).scalars()
    ]
    sources = [
        {
            'sourceResultId': str(s.source_result_id),
            'sourceRunId': str(s.source_run_id),
            'activityRecordId': str(s.activity_record_id),
            'activityDate': s.activity_date.isoformat(),
            'monthStart': s.month_start.isoformat(),
            'fuelCode': s.fuel_code,
            'fuelName': s.fuel_name,
            'datasetCode': s.dataset_code,
            'datasetVersion': s.dataset_version,
            'activityQuantity': str(s.activity_quantity),
            'activityUnit': s.activity_unit,
            'facilityFossilCo2Tonnes': str(s.facility_fossil_co2_tonnes),
            'cbamFossilCo2Tonnes': str(s.cbam_fossil_co2_tonnes),
            'nonCbamFossilCo2Tonnes': str(s.non_cbam_fossil_co2_tonnes),
            'monthlyShareRaw': str(s.monthly_share_raw),
            'facilityFuelMassKg': str(s.facility_fuel_mass_kg),
            'cbamFuelMassKg': str(s.cbam_fuel_mass_kg),
            'facilityEnergyContentTj': str(s.facility_energy_content_tj),
            'cbamEnergyContentTj': str(s.cbam_energy_content_tj),
        }
        for s in db.execute(
            select(CbamDeaSourceSnapshot)
            .where(CbamDeaSourceSnapshot.result_id == row.id)
            .order_by(CbamDeaSourceSnapshot.month_start.asc(), CbamDeaSourceSnapshot.id.asc())
        ).scalars()
    ]
    products = [
        {
            'productId': str(p.product_id),
            'productProfileVersionId': str(p.product_profile_version_id),
            'profileVersion': p.profile_version,
            'cnNormalizedCode': p.cn_normalized_code,
            'cnDisplayCode': p.cn_display_code,
            'productName': p.product_name,
            'productionRecordIds': p.production_record_ids,
            'productionQuantitySnapshots': p.production_quantity_snapshots,
            'normalizedQuantityTonnes': str(p.normalized_quantity_tonnes),
            'denominatorTonnes': str(p.denominator_tonnes),
            'rawShare': str(p.raw_share),
            'rawAllocatedFossilCo2Tonnes': str(p.raw_allocated_fossil_co2_tonnes),
            'finalAllocatedFossilCo2Tonnes': str(p.final_allocated_fossil_co2_tonnes),
            'roundingAdjustment': str(p.rounding_adjustment),
            'resultUnit': p.result_unit,
        }
        for p in db.execute(
            select(CbamDeaProductAllocation)
            .where(CbamDeaProductAllocation.result_id == row.id)
            .order_by(CbamDeaProductAllocation.product_profile_version_id.asc())
        ).scalars()
    ]
    return DirectEmissionsAllocationResultDetail(
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
        facility_fossil_co2_tonnes_raw=row.facility_fossil_co2_tonnes_raw,
        cbam_fossil_co2_tonnes_raw=row.cbam_fossil_co2_tonnes_raw,
        non_cbam_fossil_co2_tonnes_raw=row.non_cbam_fossil_co2_tonnes_raw,
        facility_fossil_co2_tonnes=row.facility_fossil_co2_tonnes,
        cbam_fossil_co2_tonnes=row.cbam_fossil_co2_tonnes,
        non_cbam_fossil_co2_tonnes=row.non_cbam_fossil_co2_tonnes,
        allocated_fossil_co2_tonnes=row.allocated_fossil_co2_tonnes,
        remaining_fossil_co2_tonnes=row.remaining_fossil_co2_tonnes,
        result_unit=row.result_unit,
        workbook_reporting_unit=row.workbook_reporting_unit,
        workbook_gas=row.workbook_gas,
        workbook_gwp=row.workbook_gwp,
        workbook_gwp_factor=row.workbook_gwp_factor,
        totals_by_month=row.totals_by_month_json,
        totals_by_fuel=row.totals_by_fuel_json,
        monthly_basis=monthly,
        source_calculations=sources,
        product_allocations=products,
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


def get_direct_emissions_allocation_summary(
    db: Session, user: User, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> DirectEmissionsAllocationPeriodSummary:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    pointer = _current_pointer(db, organization_id=organization_id, binding_id=binding_id)
    if pointer is None:
        return DirectEmissionsAllocationPeriodSummary(
            reporting_period_binding_id=binding_id,
            methodology_code=METHODOLOGY_CODE,
            current_result_id=None,
            current_is_stale=False,
            stale_reason_codes=[],
            facility_fossil_co2_tonnes=None,
            cbam_fossil_co2_tonnes=None,
            non_cbam_fossil_co2_tonnes=None,
            allocated_fossil_co2_tonnes=None,
            remaining_fossil_co2_tonnes=None,
            result_unit=RESULT_UNIT_TCO2,
            workbook_reporting_unit=WORKBOOK_REPORTING_UNIT,
            balance_status=None,
            totals_by_month={},
            totals_by_fuel={},
            totals_by_product_profile=[],
        )
    detail = get_direct_emissions_allocation_result(
        db, user, organization_id, binding_id, pointer.current_result_id
    )
    return DirectEmissionsAllocationPeriodSummary(
        reporting_period_binding_id=binding_id,
        methodology_code=METHODOLOGY_CODE,
        current_result_id=detail.result_id,
        current_is_stale=detail.is_stale,
        stale_reason_codes=detail.stale_reason_codes,
        facility_fossil_co2_tonnes=detail.facility_fossil_co2_tonnes,
        cbam_fossil_co2_tonnes=detail.cbam_fossil_co2_tonnes,
        non_cbam_fossil_co2_tonnes=detail.non_cbam_fossil_co2_tonnes,
        allocated_fossil_co2_tonnes=detail.allocated_fossil_co2_tonnes,
        remaining_fossil_co2_tonnes=detail.remaining_fossil_co2_tonnes,
        result_unit=detail.result_unit,
        workbook_reporting_unit=detail.workbook_reporting_unit,
        balance_status=detail.balance_status,
        totals_by_month=detail.totals_by_month,
        totals_by_fuel=detail.totals_by_fuel,
        totals_by_product_profile=detail.product_allocations,
    )
