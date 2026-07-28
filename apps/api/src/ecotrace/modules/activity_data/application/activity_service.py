from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.constants import (
    ROLE_ANALYST,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SUSTAINABILITY_MANAGER,
    ROLE_SYSTEM_ADMIN,
)
from ecotrace.core.exceptions import (
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.activity_data.infrastructure.models import (
    ActivityRecord,
    ActivityRecordRevision,
)
from ecotrace.modules.facilities.application.facility_service import get_facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.operational_assets.application.asset_service import (
    get_data_source,
    get_equipment,
    get_production_line,
)
from ecotrace.modules.reference_data.application.unit_conversion import normalize_quantity
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.reporting_periods.application.period_service import (
    assert_period_writable,
    get_period,
)
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import (
    ensure_org_access,
    membership_role_codes,
    require_approve,
    require_write_operational,
)
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

SORT_WHITELIST = {
    "activityDate": ActivityRecord.activity_date,
    "createdAt": ActivityRecord.created_at,
    "quantity": ActivityRecord.quantity,
    "status": ActivityRecord.status,
}


class ActivityCreate(CamelModel):
    facility_id: uuid.UUID | None = None
    production_line_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    data_source_id: uuid.UUID | None = None
    activity_type_id: uuid.UUID
    reporting_period_id: uuid.UUID
    activity_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    quantity: Decimal
    unit_code: str
    source_reference: str | None = None
    description: str | None = None
    notes: str | None = None
    metadata_json: dict[str, Any] | None = None


class ActivityUpdate(CamelModel):
    facility_id: uuid.UUID | None = None
    production_line_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    data_source_id: uuid.UUID | None = None
    activity_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    quantity: Decimal | None = None
    unit_code: str | None = None
    source_reference: str | None = None
    description: str | None = None
    notes: str | None = None
    metadata_json: dict[str, Any] | None = None
    row_version: int


class ActivityResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID | None
    production_line_id: uuid.UUID | None
    equipment_id: uuid.UUID | None
    data_source_id: uuid.UUID | None
    activity_type_id: uuid.UUID
    reporting_period_id: uuid.UUID
    activity_date: date | None
    period_start: date | None
    period_end: date | None
    quantity: Decimal
    unit_code: str
    normalized_quantity: Decimal
    normalized_unit_code: str
    status: str
    source_reference: str | None
    description: str | None
    notes: str | None
    rejection_reason: str | None
    correction_reason: str | None
    row_version: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class ReasonRequest(CamelModel):
    reason: str = ""
    row_version: int


class CorrectRequest(CamelModel):
    reason: str
    row_version: int
    quantity: Decimal | None = None
    unit_code: str | None = None
    activity_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    description: str | None = None
    notes: str | None = None
    source_reference: str | None = None


class RevisionResponse(CamelModel):
    id: uuid.UUID
    activity_record_id: uuid.UUID
    revision_number: int
    change_type: str
    changed_by_user_id: uuid.UUID | None
    previous_data_json: dict[str, Any] | None
    new_data_json: dict[str, Any] | None
    change_reason: str | None
    created_at: datetime


def _snapshot(record: ActivityRecord) -> dict[str, Any]:
    return {
        "status": record.status,
        "quantity": str(record.quantity),
        "unitCode": record.unit_code,
        "normalizedQuantity": str(record.normalized_quantity),
        "normalizedUnitCode": record.normalized_unit_code,
        "activityDate": record.activity_date.isoformat() if record.activity_date else None,
        "periodStart": record.period_start.isoformat() if record.period_start else None,
        "periodEnd": record.period_end.isoformat() if record.period_end else None,
        "facilityId": str(record.facility_id) if record.facility_id else None,
        "sourceReference": record.source_reference,
        "rowVersion": record.row_version,
    }


def _add_revision(
    db: Session,
    record: ActivityRecord,
    *,
    change_type: str,
    user: User,
    previous: dict[str, Any] | None,
    new: dict[str, Any] | None,
    reason: str | None = None,
) -> None:
    next_rev = (
        db.execute(
            select(func.coalesce(func.max(ActivityRecordRevision.revision_number), 0)).where(
                ActivityRecordRevision.activity_record_id == record.id
            )
        ).scalar_one()
        + 1
    )
    db.add(
        ActivityRecordRevision(
            activity_record_id=record.id,
            revision_number=int(next_rev),
            change_type=change_type,
            changed_by_user_id=user.id,
            previous_data_json=previous,
            new_data_json=new,
            change_reason=reason,
        )
    )


def _validate_links(
    db: Session,
    organization_id: uuid.UUID,
    *,
    activity_type: ActivityType,
    facility_id: uuid.UUID | None,
    production_line_id: uuid.UUID | None,
    equipment_id: uuid.UUID | None,
    data_source_id: uuid.UUID | None,
    activity_date: date | None,
    period_start: date | None,
    period_end: date | None,
    period_id: uuid.UUID,
) -> None:
    period = get_period(db, organization_id, period_id)
    assert_period_writable(period)
    if activity_type.requires_facility and facility_id is None:
        raise ValidationAppError("Facility is required for this activity type.")
    if activity_type.requires_equipment and equipment_id is None:
        raise ValidationAppError("Equipment is required for this activity type.")
    if facility_id:
        get_facility(db, organization_id, facility_id)
    if production_line_id:
        line = get_production_line(db, organization_id, production_line_id)
        if facility_id and line.facility_id != facility_id:
            raise ValidationAppError("Production line must belong to the selected facility.")
    if equipment_id:
        eq = get_equipment(db, organization_id, equipment_id)
        if facility_id and eq.facility_id != facility_id:
            raise ValidationAppError("Equipment must belong to the selected facility.")
    if data_source_id:
        get_data_source(db, organization_id, data_source_id)
    check_date = activity_date or period_start
    if check_date and (check_date < period.start_date or check_date > period.end_date):
        raise ValidationAppError("Activity date must fall within the reporting period.")
    if period_start and period_end:
        if period_end < period_start:
            raise ValidationAppError("periodEnd cannot be earlier than periodStart.")
        if period_start < period.start_date or period_end > period.end_date:
            raise ValidationAppError("Activity period range must fall within the reporting period.")


def get_record(db: Session, organization_id: uuid.UUID, record_id: uuid.UUID) -> ActivityRecord:
    record = db.get(ActivityRecord, record_id)
    if record is None or record.organization_id != organization_id:
        raise NotFoundError("Activity record not found.")
    return record


def list_records(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    activity_type_id: uuid.UUID | None = None,
    reporting_period_id: uuid.UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    sort_by: str = "createdAt",
    sort_direction: str = "desc",
) -> Page[ActivityResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(ActivityRecord).where(
        ActivityRecord.organization_id == organization_id,
        ActivityRecord.is_archived.is_(False),
    )
    if facility_id:
        stmt = stmt.where(ActivityRecord.facility_id == facility_id)
    if activity_type_id:
        stmt = stmt.where(ActivityRecord.activity_type_id == activity_type_id)
    if reporting_period_id:
        stmt = stmt.where(ActivityRecord.reporting_period_id == reporting_period_id)
    if status:
        stmt = stmt.where(ActivityRecord.status == status)
    if date_from:
        stmt = stmt.where(ActivityRecord.activity_date >= date_from)
    if date_to:
        stmt = stmt.where(ActivityRecord.activity_date <= date_to)
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                ActivityRecord.source_reference.ilike(like),
                ActivityRecord.description.ilike(like),
            )
        )
    col = SORT_WHITELIST.get(sort_by, ActivityRecord.created_at)
    order = col.desc() if sort_direction.lower() == "desc" else col.asc()
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(stmt.order_by(order).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return paginate(
        [ActivityResponse.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def create_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: ActivityCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    require_write_operational(db, user, organization_id)
    if payload.quantity < 0:
        raise ValidationAppError("Quantity must be greater than or equal to zero.")
    activity_type = db.get(ActivityType, payload.activity_type_id)
    if activity_type is None or not activity_type.is_active:
        raise ValidationAppError("Activity type not found or inactive.")
    _validate_links(
        db,
        organization_id,
        activity_type=activity_type,
        facility_id=payload.facility_id,
        production_line_id=payload.production_line_id,
        equipment_id=payload.equipment_id,
        data_source_id=payload.data_source_id,
        activity_date=payload.activity_date,
        period_start=payload.period_start,
        period_end=payload.period_end,
        period_id=payload.reporting_period_id,
    )
    normalized, normalized_unit = normalize_quantity(
        db,
        quantity=payload.quantity,
        unit_code=payload.unit_code,
        activity_type=activity_type,
    )
    record = ActivityRecord(
        organization_id=organization_id,
        facility_id=payload.facility_id,
        production_line_id=payload.production_line_id,
        equipment_id=payload.equipment_id,
        data_source_id=payload.data_source_id,
        activity_type_id=payload.activity_type_id,
        reporting_period_id=payload.reporting_period_id,
        activity_date=payload.activity_date,
        period_start=payload.period_start,
        period_end=payload.period_end,
        quantity=payload.quantity,
        unit_code=payload.unit_code,
        normalized_quantity=normalized,
        normalized_unit_code=normalized_unit,
        status="draft",
        source_reference=payload.source_reference,
        description=payload.description,
        notes=payload.notes,
        metadata_json=payload.metadata_json,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        row_version=1,
    )
    db.add(record)
    db.flush()
    _add_revision(
        db,
        record,
        change_type="created",
        user=user,
        previous=None,
        new=_snapshot(record),
    )
    write_audit_log(
        db,
        action="activity_record.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def _check_version(record: ActivityRecord, row_version: int) -> None:
    if record.row_version != row_version:
        raise ConflictError("The record was modified by another user. Refresh and try again.")


def update_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ActivityUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    require_write_operational(db, user, organization_id)
    record = get_record(db, organization_id, record_id)
    _check_version(record, payload.row_version)
    if record.status not in {"draft", "rejected"}:
        raise BusinessRuleError("Only draft or rejected records can be edited directly.")
    period = get_period(db, organization_id, record.reporting_period_id)
    assert_period_writable(period)
    previous = _snapshot(record)
    data = payload.model_dump(exclude_unset=True, exclude={"row_version"})
    activity_type = db.get(ActivityType, record.activity_type_id)
    assert activity_type is not None
    quantity = data.get("quantity", record.quantity)
    unit_code = data.get("unit_code", record.unit_code)
    if quantity < 0:
        raise ValidationAppError("Quantity must be greater than or equal to zero.")
    for key, value in data.items():
        setattr(record, key, value)
    _validate_links(
        db,
        organization_id,
        activity_type=activity_type,
        facility_id=record.facility_id,
        production_line_id=record.production_line_id,
        equipment_id=record.equipment_id,
        data_source_id=record.data_source_id,
        activity_date=record.activity_date,
        period_start=record.period_start,
        period_end=record.period_end,
        period_id=record.reporting_period_id,
    )
    normalized, normalized_unit = normalize_quantity(
        db, quantity=quantity, unit_code=unit_code, activity_type=activity_type
    )
    record.normalized_quantity = normalized
    record.normalized_unit_code = normalized_unit
    if record.status == "rejected":
        record.status = "draft"
        record.rejection_reason = None
    record.row_version += 1
    record.updated_by_user_id = user.id
    _add_revision(
        db,
        record,
        change_type="updated",
        user=user,
        previous=previous,
        new=_snapshot(record),
    )
    write_audit_log(
        db,
        action="activity_record.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def submit_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ReasonRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    require_write_operational(db, user, organization_id)
    record = get_record(db, organization_id, record_id)
    _check_version(record, payload.row_version)
    period = get_period(db, organization_id, record.reporting_period_id)
    assert_period_writable(period)
    if record.status != "draft":
        raise BusinessRuleError("Only draft records can be submitted.")
    previous = _snapshot(record)
    record.status = "submitted"
    record.submitted_at = datetime.now(UTC)
    record.submitted_by_user_id = user.id
    record.row_version += 1
    record.updated_by_user_id = user.id
    _add_revision(
        db,
        record,
        change_type="submitted",
        user=user,
        previous=previous,
        new=_snapshot(record),
        reason=payload.reason,
    )
    write_audit_log(
        db,
        action="activity_record.submitted",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def approve_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ReasonRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    require_approve(db, user, organization_id)
    record = get_record(db, organization_id, record_id)
    _check_version(record, payload.row_version)
    period = get_period(db, organization_id, record.reporting_period_id)
    assert_period_writable(period)
    if record.status != "submitted":
        raise BusinessRuleError("Only submitted records can be approved.")
    previous = _snapshot(record)
    record.status = "approved"
    record.approved_at = datetime.now(UTC)
    record.approved_by_user_id = user.id
    record.row_version += 1
    record.updated_by_user_id = user.id
    _add_revision(
        db,
        record,
        change_type="approved",
        user=user,
        previous=previous,
        new=_snapshot(record),
        reason=payload.reason,
    )
    write_audit_log(
        db,
        action="activity_record.approved",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def reject_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ReasonRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    require_approve(db, user, organization_id)
    if not payload.reason.strip():
        raise ValidationAppError("Rejection reason is required.")
    record = get_record(db, organization_id, record_id)
    _check_version(record, payload.row_version)
    period = get_period(db, organization_id, record.reporting_period_id)
    assert_period_writable(period)
    if record.status != "submitted":
        raise BusinessRuleError("Only submitted records can be rejected.")
    previous = _snapshot(record)
    record.status = "rejected"
    record.rejection_reason = payload.reason.strip()
    record.row_version += 1
    record.updated_by_user_id = user.id
    _add_revision(
        db,
        record,
        change_type="rejected",
        user=user,
        previous=previous,
        new=_snapshot(record),
        reason=payload.reason,
    )
    write_audit_log(
        db,
        action="activity_record.rejected",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def correct_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: CorrectRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    require_approve(db, user, organization_id)
    if not payload.reason.strip():
        raise ValidationAppError("Correction reason is required.")
    record = get_record(db, organization_id, record_id)
    _check_version(record, payload.row_version)
    period = get_period(db, organization_id, record.reporting_period_id)
    assert_period_writable(period)
    if record.status != "approved":
        raise BusinessRuleError("Only approved records can be corrected.")
    previous = _snapshot(record)
    activity_type = db.get(ActivityType, record.activity_type_id)
    assert activity_type is not None
    if payload.quantity is not None:
        record.quantity = payload.quantity
    if payload.unit_code is not None:
        record.unit_code = payload.unit_code
    if payload.activity_date is not None:
        record.activity_date = payload.activity_date
    if payload.period_start is not None:
        record.period_start = payload.period_start
    if payload.period_end is not None:
        record.period_end = payload.period_end
    if payload.description is not None:
        record.description = payload.description
    if payload.notes is not None:
        record.notes = payload.notes
    if payload.source_reference is not None:
        record.source_reference = payload.source_reference
    if record.quantity < 0:
        raise ValidationAppError("Quantity must be greater than or equal to zero.")
    normalized, normalized_unit = normalize_quantity(
        db,
        quantity=record.quantity,
        unit_code=record.unit_code,
        activity_type=activity_type,
    )
    record.normalized_quantity = normalized
    record.normalized_unit_code = normalized_unit
    record.correction_reason = payload.reason.strip()
    record.status = "submitted"
    record.submitted_at = datetime.now(UTC)
    record.submitted_by_user_id = user.id
    record.approved_at = None
    record.approved_by_user_id = None
    record.row_version += 1
    record.updated_by_user_id = user.id
    _add_revision(
        db,
        record,
        change_type="corrected",
        user=user,
        previous=previous,
        new=_snapshot(record),
        reason=payload.reason,
    )
    write_audit_log(
        db,
        action="activity_record.corrected",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def archive_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ReasonRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityResponse:
    codes = membership_role_codes(db, user, organization_id)
    if not codes.intersection(
        {
            ROLE_SYSTEM_ADMIN,
            ROLE_ORGANIZATION_ADMIN,
            ROLE_ANALYST,
            ROLE_SUSTAINABILITY_MANAGER,
        }
    ):
        raise AuthorizationError()
    record = get_record(db, organization_id, record_id)
    _check_version(record, payload.row_version)
    period = get_period(db, organization_id, record.reporting_period_id)
    assert_period_writable(period)
    previous = _snapshot(record)
    record.status = "archived"
    record.is_archived = True
    record.row_version += 1
    record.updated_by_user_id = user.id
    _add_revision(
        db,
        record,
        change_type="archived",
        user=user,
        previous=previous,
        new=_snapshot(record),
        reason=payload.reason,
    )
    write_audit_log(
        db,
        action="activity_record.archived",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="activity_record",
        entity_id=str(record.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(record)
    return ActivityResponse.model_validate(record)


def list_revisions(
    db: Session, user: User, organization_id: uuid.UUID, record_id: uuid.UUID
) -> list[RevisionResponse]:
    ensure_org_access(db, user, organization_id)
    get_record(db, organization_id, record_id)
    rows = list(
        db.execute(
            select(ActivityRecordRevision)
            .where(ActivityRecordRevision.activity_record_id == record_id)
            .order_by(ActivityRecordRevision.revision_number.asc())
        )
        .scalars()
        .all()
    )
    return [RevisionResponse.model_validate(r) for r in rows]
