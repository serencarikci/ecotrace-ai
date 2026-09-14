"""Monthly production-basis (workbook D/E) data foundation.

Does not perform direct-emissions allocation.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.catalogs import (
    MASS_ACTIVITY_UNITS,
    kg_to_tonnes,
    mass_to_kg,
    require_unit,
)
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.ports import ReportingPeriodRef
from ecotrace.modules.cbam.application.production_profile_link import (
    compute_profile_link_state,
    is_allocation_eligible_link,
)
from ecotrace.modules.cbam.application.stationary_combustion_current_result_service import (
    get_current_result_ids_for_binding,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamActivityRecord,
    CbamMonthlyProductionBasis,
    CbamProductionRecord,
    CbamReportingPeriodBinding,
)
from ecotrace.modules.cbam.infrastructure.reporting_period_reference_adapter import (
    require_reporting_period_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

RECORD_STATUS = Literal["INCOMPLETE", "INVALID", "READY"]
RECONCILIATION_STATUS = Literal["EXACT_MATCH", "MISMATCH", "UNAVAILABLE"]
MONTH_COVERAGE = Literal["MISSING", "INCOMPLETE", "INVALID", "READY"]
COMBUSTION_COMPAT = Literal["READY", "BLOCKED"]

SHARE_QUANTUM = Decimal("0.000000000001")
SOURCE_TYPES = frozenset({"MANUAL", "IMPORT", "SYSTEM"})


class MonthlyProductionBasisCreate(CamelModel):
    month_start: date
    total_production_quantity: Decimal | None = None
    cbam_quantity: Decimal | None = None
    quantity_unit: str = "t"
    source_type: str = "MANUAL"
    notes: str | None = None


class MonthlyProductionBasisUpdate(CamelModel):
    row_version: int
    total_production_quantity: Decimal | None = None
    cbam_quantity: Decimal | None = None
    quantity_unit: str | None = None
    source_type: str | None = None
    notes: str | None = None


class MonthlyProductionBasisResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    month_start: date
    total_production_quantity: Decimal | None
    cbam_quantity: Decimal | None
    quantity_unit: str
    normalized_total_production_tonnes: Decimal | None
    normalized_cbam_quantity_tonnes: Decimal | None
    cbam_share: Decimal | None
    status: RECORD_STATUS
    issue_codes: list[str]
    source_type: str
    notes: str | None
    row_version: int


class MonthCoverageItem(CamelModel):
    month_start: date
    coverage: MONTH_COVERAGE
    record_id: uuid.UUID | None
    issue_codes: list[str]


class ProductionReconciliationMonth(CamelModel):
    month_start: date
    explicit_cbam_quantity_tonnes: Decimal | None
    recorded_cbam_production_tonnes: Decimal | None
    difference_tonnes: Decimal | None
    reconciliation_status: RECONCILIATION_STATUS


class CombustionCompatibilityItem(CamelModel):
    activity_record_id: uuid.UUID
    current_result_id: uuid.UUID
    activity_date: date | None
    month_start: date | None
    status: COMBUSTION_COMPAT
    issue_codes: list[str]


class MonthlyProductionBasisSummary(CamelModel):
    reporting_period_binding_id: uuid.UUID
    expected_month_count: int
    completed_month_count: int
    incomplete_month_count: int
    invalid_month_count: int
    missing_month_count: int
    status: RECORD_STATUS
    allocation_basis_ready: bool
    blocking_issue_codes: list[str]
    month_coverage: list[MonthCoverageItem]
    # Informational sums only — never use sum(E)/sum(D) for allocation.
    informational_total_production_tonnes: Decimal | None
    informational_total_cbam_quantity_tonnes: Decimal | None
    combustion_compatibility_status: COMBUSTION_COMPAT
    combustion_compatibility_issue_codes: list[str]
    combustion_items: list[CombustionCompatibilityItem]
    production_reconciliation: list[ProductionReconciliationMonth]


def canonical_month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def month_end(month_start: date) -> date:
    last = calendar.monthrange(month_start.year, month_start.month)[1]
    return date(month_start.year, month_start.month, last)


def iter_expected_months(period_start: date, period_end: date) -> list[date]:
    """Months that overlap the reporting period (canonical first-of-month keys)."""
    if period_end < period_start:
        return []
    cur = canonical_month_start(period_start)
    last = canonical_month_start(period_end)
    out: list[date] = []
    while cur <= last:
        out.append(cur)
        cur = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)
    return out


def month_overlaps_period(month_start: date, period_start: date, period_end: date) -> bool:
    return month_start <= period_end and month_end(month_start) >= period_start


def require_mass_unit(unit: str) -> str:
    normalized = require_unit(unit)
    if normalized not in MASS_ACTIVITY_UNITS:
        raise ValidationAppError(
            "Monthly production-basis quantities must use a mass unit (kg, t, or Gg).",
            details=[{"code": "INCOMPATIBLE_PRODUCTION_UNIT", "field": "quantityUnit"}],
        )
    return normalized


def to_tonnes(quantity: Decimal, unit: str) -> Decimal:
    kg = mass_to_kg(quantity, unit)
    if kg is None:
        raise ValidationAppError(
            "Unsupported mass unit for tonne normalization.",
            details=[{"code": "INCOMPATIBLE_PRODUCTION_UNIT"}],
        )
    return kg_to_tonnes(kg)


def _validate_quantities(
    *,
    total: Decimal | None,
    cbam: Decimal | None,
    unit: str,
) -> list[str]:
    codes: list[str] = []
    if total is not None and total < 0:
        raise ValidationAppError(
            "Total production quantity cannot be negative.",
            details=[{"code": "INVALID_QUANTITY", "field": "totalProductionQuantity"}],
        )
    if cbam is not None and cbam < 0:
        raise ValidationAppError(
            "CBAM quantity cannot be negative.",
            details=[{"code": "INVALID_QUANTITY", "field": "cbamQuantity"}],
        )
    if total is None:
        codes.append("TOTAL_PRODUCTION_REQUIRED")
    if cbam is None:
        codes.append("CBAM_QUANTITY_REQUIRED")
    if total is not None and cbam is not None:
        total_t = to_tonnes(total, unit)
        cbam_t = to_tonnes(cbam, unit)
        if cbam_t > 0 and total_t <= 0:
            codes.append("TOTAL_PRODUCTION_MUST_BE_POSITIVE")
        if cbam_t > total_t:
            codes.append("CBAM_QUANTITY_EXCEEDS_TOTAL")
    return codes


def _compute_status_and_share(
    *,
    total: Decimal | None,
    cbam: Decimal | None,
    unit: str,
) -> tuple[RECORD_STATUS, list[str], Decimal | None, Decimal | None, Decimal | None]:
    try:
        require_mass_unit(unit)
    except ValidationAppError:
        return (
            "INVALID",
            ["INCOMPATIBLE_PRODUCTION_UNIT"],
            None,
            None,
            None,
        )
    issue_codes = _validate_quantities(total=total, cbam=cbam, unit=unit)
    total_t = to_tonnes(total, unit) if total is not None else None
    cbam_t = to_tonnes(cbam, unit) if cbam is not None else None
    hard = {
        "TOTAL_PRODUCTION_MUST_BE_POSITIVE",
        "CBAM_QUANTITY_EXCEEDS_TOTAL",
        "INCOMPATIBLE_PRODUCTION_UNIT",
    }
    if any(c in hard for c in issue_codes):
        return "INVALID", issue_codes, total_t, cbam_t, None
    if total is None or cbam is None:
        return "INCOMPLETE", issue_codes, total_t, cbam_t, None
    if total_t is None or total_t == 0:
        return "READY", [], total_t, cbam_t, None
    assert cbam_t is not None
    share = (cbam_t / total_t).quantize(SHARE_QUANTUM)
    return "READY", [], total_t, cbam_t, share


def _to_response(row: CbamMonthlyProductionBasis) -> MonthlyProductionBasisResponse:
    status, codes, total_t, cbam_t, share = _compute_status_and_share(
        total=row.total_production_quantity,
        cbam=row.cbam_quantity,
        unit=row.quantity_unit,
    )
    return MonthlyProductionBasisResponse(
        id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        month_start=row.month_start,
        total_production_quantity=row.total_production_quantity,
        cbam_quantity=row.cbam_quantity,
        quantity_unit=row.quantity_unit,
        normalized_total_production_tonnes=total_t,
        normalized_cbam_quantity_tonnes=cbam_t,
        cbam_share=share,
        status=status,
        issue_codes=codes,
        source_type=row.source_type,
        notes=row.notes,
        row_version=row.row_version,
    )


def _get_row(
    db: Session, organization_id: uuid.UUID, record_id: uuid.UUID
) -> CbamMonthlyProductionBasis:
    row = db.get(CbamMonthlyProductionBasis, record_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("CBAM monthly production-basis record not found.")
    return row


def _period_for_binding(
    db: Session, organization_id: uuid.UUID, binding: CbamReportingPeriodBinding
) -> ReportingPeriodRef:
    return require_reporting_period_in_organization(
        db, organization_id, binding.reporting_period_id
    )


def _reject_hard_invalid_on_write(
    *,
    total: Decimal | None,
    cbam: Decimal | None,
    unit: str,
) -> None:
    """Reject write when both values are present but violate workbook rules."""
    require_mass_unit(unit)
    codes = _validate_quantities(total=total, cbam=cbam, unit=unit)
    hard = {
        "TOTAL_PRODUCTION_MUST_BE_POSITIVE",
        "CBAM_QUANTITY_EXCEEDS_TOTAL",
    }
    for code in codes:
        if code in hard:
            messages = {
                "TOTAL_PRODUCTION_MUST_BE_POSITIVE": (
                    "Total production (workbook D) must be greater than zero when "
                    "CBAM quantity (workbook E) is greater than zero."
                ),
                "CBAM_QUANTITY_EXCEEDS_TOTAL": (
                    "CBAM quantity (workbook E) cannot exceed total production (workbook D)."
                ),
            }
            raise BusinessRuleError(messages[code], details=[{"code": code}])


def list_monthly_production_basis(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[MonthlyProductionBasisResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = (
        select(CbamMonthlyProductionBasis)
        .where(
            CbamMonthlyProductionBasis.organization_id == organization_id,
            CbamMonthlyProductionBasis.reporting_period_binding_id == binding_id,
        )
        .order_by(CbamMonthlyProductionBasis.month_start.asc())
    )
    rows = list(db.execute(stmt).scalars().all())
    items = [_to_response(r) for r in rows]
    start = (page - 1) * page_size
    page_items = items[start : start + page_size]
    return paginate(page_items, page=page, page_size=page_size, total_items=len(items))


def get_monthly_production_basis(
    db: Session, user: User, organization_id: uuid.UUID, record_id: uuid.UUID
) -> MonthlyProductionBasisResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_row(db, organization_id, record_id))


def create_monthly_production_basis(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: MonthlyProductionBasisCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> MonthlyProductionBasisResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    period = _period_for_binding(db, organization_id, binding)
    if payload.month_start != canonical_month_start(payload.month_start):
        raise ValidationAppError(
            "monthStart must be the first calendar day of the month.",
            details=[{"code": "MONTH_OUTSIDE_REPORTING_PERIOD", "field": "monthStart"}],
        )
    if not month_overlaps_period(payload.month_start, period.start_date, period.end_date):
        raise BusinessRuleError(
            "Month is outside the reporting period.",
            details=[{"code": "MONTH_OUTSIDE_REPORTING_PERIOD"}],
        )
    unit = require_mass_unit(payload.quantity_unit)
    if payload.source_type not in SOURCE_TYPES:
        raise ValidationAppError("Invalid sourceType.")
    _reject_hard_invalid_on_write(
        total=payload.total_production_quantity,
        cbam=payload.cbam_quantity,
        unit=unit,
    )
    existing = db.execute(
        select(CbamMonthlyProductionBasis.id).where(
            CbamMonthlyProductionBasis.organization_id == organization_id,
            CbamMonthlyProductionBasis.reporting_period_binding_id == binding.id,
            CbamMonthlyProductionBasis.month_start == payload.month_start,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "A monthly production-basis row already exists for this month.",
            details=[{"code": "MONTHLY_PRODUCTION_BASIS_DUPLICATE"}],
        )
    row = CbamMonthlyProductionBasis(
        organization_id=organization_id,
        reporting_period_binding_id=binding.id,
        month_start=payload.month_start,
        total_production_quantity=payload.total_production_quantity,
        cbam_quantity=payload.cbam_quantity,
        quantity_unit=unit,
        source_type=payload.source_type,
        notes=payload.notes,
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError as exc:
        raise ConflictError(
            "A monthly production-basis row already exists for this month.",
            details=[{"code": "MONTHLY_PRODUCTION_BASIS_DUPLICATE"}],
        ) from exc
    write_audit_log(
        db,
        action="cbam.monthly_production_basis.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_monthly_production_basis",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "bindingId": str(binding.id),
            "monthStart": row.month_start.isoformat(),
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_monthly_production_basis(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: MonthlyProductionBasisUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> MonthlyProductionBasisResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity="CBAM monthly production basis")
    data = payload.model_dump(exclude_unset=True, exclude={"row_version"})
    unit = row.quantity_unit
    if "quantity_unit" in data and data["quantity_unit"] is not None:
        unit = require_mass_unit(data["quantity_unit"])
        row.quantity_unit = unit
    if "source_type" in data and data["source_type"] is not None:
        if data["source_type"] not in SOURCE_TYPES:
            raise ValidationAppError("Invalid sourceType.")
        row.source_type = data["source_type"]
    if "notes" in data:
        row.notes = data["notes"]
    if "total_production_quantity" in data:
        row.total_production_quantity = data["total_production_quantity"]
    if "cbam_quantity" in data:
        row.cbam_quantity = data["cbam_quantity"]
    _reject_hard_invalid_on_write(
        total=row.total_production_quantity,
        cbam=row.cbam_quantity,
        unit=row.quantity_unit,
    )
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.monthly_production_basis.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_monthly_production_basis",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"fields": list(data.keys()), "rowVersion": row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def delete_monthly_production_basis(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Hard-delete draft input. Completed allocation snapshots block deletion."""
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
        assert_monthly_basis_not_referenced,
    )

    assert_monthly_basis_not_referenced(db, organization_id=organization_id, basis_record_id=row.id)
    write_audit_log(
        db,
        action="cbam.monthly_production_basis.deleted",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_monthly_production_basis",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"monthStart": row.month_start.isoformat()},
    )
    db.delete(row)
    db.commit()


def _load_rows_for_binding(
    db: Session, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> dict[date, CbamMonthlyProductionBasis]:
    rows = list(
        db.execute(
            select(CbamMonthlyProductionBasis).where(
                CbamMonthlyProductionBasis.organization_id == organization_id,
                CbamMonthlyProductionBasis.reporting_period_binding_id == binding_id,
            )
        )
        .scalars()
        .all()
    )
    return {r.month_start: r for r in rows}


def _combustion_compatibility(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    expected: list[date],
    rows_by_month: dict[date, CbamMonthlyProductionBasis],
) -> tuple[COMBUSTION_COMPAT, list[str], list[CombustionCompatibilityItem]]:
    pointer_map = get_current_result_ids_for_binding(
        db, organization_id=organization_id, binding_id=binding_id
    )
    if not pointer_map:
        return "READY", [], []
    activity_ids = list(pointer_map.keys())
    activities = {
        a.id: a
        for a in db.execute(
            select(CbamActivityRecord).where(CbamActivityRecord.id.in_(activity_ids))
        )
        .scalars()
        .all()
    }
    items: list[CombustionCompatibilityItem] = []
    blocking: list[str] = []
    for activity_id, result_id in pointer_map.items():
        activity = activities.get(activity_id)
        codes: list[str] = []
        act_date = activity.activity_date if activity is not None else None
        month: date | None = None
        if act_date is None:
            codes.append("COMBUSTION_ACTIVITY_DATE_REQUIRED")
        else:
            month = canonical_month_start(act_date)
            if month not in expected:
                codes.append("COMBUSTION_MONTH_NOT_COVERED")
            else:
                basis = rows_by_month.get(month)
                if basis is None:
                    codes.append("MONTHLY_PRODUCTION_BASIS_NOT_READY")
                    codes.append("MONTHLY_PRODUCTION_BASIS_MISSING")
                else:
                    row_status, _, *_rest = _compute_status_and_share(
                        total=basis.total_production_quantity,
                        cbam=basis.cbam_quantity,
                        unit=basis.quantity_unit,
                    )
                    if row_status != "READY":
                        codes.append("MONTHLY_PRODUCTION_BASIS_NOT_READY")
        item_status: COMBUSTION_COMPAT = "BLOCKED" if codes else "READY"
        if codes:
            for c in codes:
                if c not in blocking:
                    blocking.append(c)
        items.append(
            CombustionCompatibilityItem(
                activity_record_id=activity_id,
                current_result_id=result_id,
                activity_date=act_date,
                month_start=month,
                status=item_status,
                issue_codes=codes,
            )
        )
    overall: COMBUSTION_COMPAT = "BLOCKED" if blocking else "READY"
    return overall, blocking, items


def _production_reconciliation(
    db: Session,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    expected: list[date],
    rows_by_month: dict[date, CbamMonthlyProductionBasis],
) -> list[ProductionReconciliationMonth]:
    productions = list(
        db.execute(
            select(CbamProductionRecord).where(
                CbamProductionRecord.organization_id == organization_id,
                CbamProductionRecord.reporting_period_binding_id == binding_id,
                CbamProductionRecord.status == "active",
            )
        )
        .scalars()
        .all()
    )
    eligible: list[CbamProductionRecord] = []
    undated = False
    for prod in productions:
        link_status, _, _ = compute_profile_link_state(db, prod)
        if not is_allocation_eligible_link(link_status):
            continue
        if prod.production_date is None:
            undated = True
            continue
        eligible.append(prod)

    out: list[ProductionReconciliationMonth] = []
    for month in expected:
        basis = rows_by_month.get(month)
        explicit = None
        if basis is not None and basis.cbam_quantity is not None:
            try:
                explicit = to_tonnes(basis.cbam_quantity, basis.quantity_unit)
            except ValidationAppError:
                explicit = None
        if undated:
            out.append(
                ProductionReconciliationMonth(
                    month_start=month,
                    explicit_cbam_quantity_tonnes=explicit,
                    recorded_cbam_production_tonnes=None,
                    difference_tonnes=None,
                    reconciliation_status="UNAVAILABLE",
                )
            )
            continue
        recorded = Decimal("0")
        unavailable = False
        for prod in eligible:
            assert prod.production_date is not None
            if canonical_month_start(prod.production_date) != month:
                continue
            try:
                recorded += to_tonnes(prod.quantity, prod.unit)
            except ValidationAppError:
                unavailable = True
                break
        if unavailable:
            out.append(
                ProductionReconciliationMonth(
                    month_start=month,
                    explicit_cbam_quantity_tonnes=explicit,
                    recorded_cbam_production_tonnes=None,
                    difference_tonnes=None,
                    reconciliation_status="UNAVAILABLE",
                )
            )
        elif explicit is None:
            out.append(
                ProductionReconciliationMonth(
                    month_start=month,
                    explicit_cbam_quantity_tonnes=None,
                    recorded_cbam_production_tonnes=recorded,
                    difference_tonnes=None,
                    reconciliation_status="UNAVAILABLE",
                )
            )
        else:
            diff = explicit - recorded
            status: RECONCILIATION_STATUS = "EXACT_MATCH" if diff == 0 else "MISMATCH"
            out.append(
                ProductionReconciliationMonth(
                    month_start=month,
                    explicit_cbam_quantity_tonnes=explicit,
                    recorded_cbam_production_tonnes=recorded,
                    difference_tonnes=diff,
                    reconciliation_status=status,
                )
            )
    return out


def get_monthly_production_basis_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> MonthlyProductionBasisSummary:
    require_cbam_view(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    period = _period_for_binding(db, organization_id, binding)
    expected = iter_expected_months(period.start_date, period.end_date)
    rows_by_month = _load_rows_for_binding(db, organization_id, binding_id)

    coverage: list[MonthCoverageItem] = []
    completed = 0
    incomplete = 0
    invalid = 0
    missing = 0
    blocking: list[str] = []
    info_total = Decimal("0")
    info_cbam = Decimal("0")
    has_total = False
    has_cbam = False

    for month in expected:
        row = rows_by_month.get(month)
        if row is None:
            missing += 1
            coverage.append(
                MonthCoverageItem(
                    month_start=month,
                    coverage="MISSING",
                    record_id=None,
                    issue_codes=["MONTHLY_PRODUCTION_BASIS_MISSING"],
                )
            )
            if "MONTHLY_PRODUCTION_BASIS_MISSING" not in blocking:
                blocking.append("MONTHLY_PRODUCTION_BASIS_MISSING")
            continue
        resp = _to_response(row)
        if resp.status == "READY":
            completed += 1
            cov: MONTH_COVERAGE = "READY"
        elif resp.status == "INVALID":
            invalid += 1
            cov = "INVALID"
            for code in resp.issue_codes:
                if code not in blocking:
                    blocking.append(code)
        else:
            incomplete += 1
            cov = "INCOMPLETE"
            for code in resp.issue_codes:
                if code not in blocking:
                    blocking.append(code)
        if resp.normalized_total_production_tonnes is not None:
            info_total += resp.normalized_total_production_tonnes
            has_total = True
        if resp.normalized_cbam_quantity_tonnes is not None:
            info_cbam += resp.normalized_cbam_quantity_tonnes
            has_cbam = True
        coverage.append(
            MonthCoverageItem(
                month_start=month,
                coverage=cov,
                record_id=row.id,
                issue_codes=list(resp.issue_codes),
            )
        )

    comb_status, comb_codes, comb_items = _combustion_compatibility(
        db, organization_id, binding_id, expected, rows_by_month
    )
    for code in comb_codes:
        if code not in blocking:
            blocking.append(code)

    allocation_ready = (
        missing == 0
        and incomplete == 0
        and invalid == 0
        and completed == len(expected)
        and len(expected) > 0
        and comb_status == "READY"
    )
    if len(expected) == 0:
        blocking.append("MONTHLY_PRODUCTION_BASIS_MISSING")
        status: RECORD_STATUS = "INVALID"
    elif allocation_ready:
        status = "READY"
    elif invalid > 0:
        status = "INVALID"
    else:
        status = "INCOMPLETE"

    reconciliation = _production_reconciliation(
        db, organization_id, binding_id, expected, rows_by_month
    )

    return MonthlyProductionBasisSummary(
        reporting_period_binding_id=binding_id,
        expected_month_count=len(expected),
        completed_month_count=completed,
        incomplete_month_count=incomplete,
        invalid_month_count=invalid,
        missing_month_count=missing,
        status=status,
        allocation_basis_ready=allocation_ready,
        blocking_issue_codes=blocking,
        month_coverage=coverage,
        informational_total_production_tonnes=info_total if has_total else None,
        informational_total_cbam_quantity_tonnes=info_cbam if has_cbam else None,
        combustion_compatibility_status=comb_status,
        combustion_compatibility_issue_codes=comb_codes,
        combustion_items=comb_items,
        production_reconciliation=reconciliation,
    )
