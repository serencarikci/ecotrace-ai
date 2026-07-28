from __future__ import annotations
import uuid
from datetime import UTC, date, datetime
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.ops_constants import PERIOD_STATUSES, PERIOD_TYPES
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_period_lock, require_period_manage, require_period_unlock
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class PeriodCreate(CamelModel):
    code: str
    name: str
    period_type: str
    start_date: date
    end_date: date
    status: str = 'open'

class PeriodUpdate(CamelModel):
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None

class PeriodResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    period_type: str
    start_date: date
    end_date: date
    status: str
    locked_at: datetime | None
    locked_by_user_id: uuid.UUID | None
    activity_record_count: int = 0

def get_period(db: Session, organization_id: uuid.UUID, period_id: uuid.UUID) -> ReportingPeriod:
    period = db.get(ReportingPeriod, period_id)
    if period is None or period.organization_id != organization_id:
        raise NotFoundError('Reporting period not found.')
    return period

def _ensure_no_same_type_overlap(db: Session, organization_id: uuid.UUID, period_type: str, start: date, end: date, exclude_id: uuid.UUID | None=None) -> None:
    stmt = select(ReportingPeriod).where(ReportingPeriod.organization_id == organization_id, ReportingPeriod.period_type == period_type, ReportingPeriod.status != 'archived', and_(ReportingPeriod.start_date <= end, ReportingPeriod.end_date >= start))
    if exclude_id:
        stmt = stmt.where(ReportingPeriod.id != exclude_id)
    if db.execute(stmt).scalars().first() is not None:
        raise ConflictError('Overlapping reporting periods of the same type are not allowed.')

def list_periods(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, status: str | None=None, period_type: str | None=None, search: str | None=None) -> Page[PeriodResponse]:
    ensure_org_access(db, user, organization_id)
    from sqlalchemy import or_
    from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
    stmt = select(ReportingPeriod).where(ReportingPeriod.organization_id == organization_id)
    if status:
        stmt = stmt.where(ReportingPeriod.status == status)
    if period_type:
        stmt = stmt.where(ReportingPeriod.period_type == period_type)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(ReportingPeriod.name.ilike(like), ReportingPeriod.code.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(ReportingPeriod.start_date.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    items: list[PeriodResponse] = []
    for row in rows:
        count = db.execute(select(func.count()).select_from(ActivityRecord).where(ActivityRecord.reporting_period_id == row.id)).scalar_one()
        resp = PeriodResponse.model_validate(row)
        resp.activity_record_count = int(count)
        items.append(resp)
    return paginate(items, page=page, page_size=page_size, total_items=int(total))

def create_period(db: Session, user: User, organization_id: uuid.UUID, payload: PeriodCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PeriodResponse:
    require_period_manage(db, user, organization_id)
    if payload.period_type not in PERIOD_TYPES:
        raise ValidationAppError('Invalid period type.')
    if payload.status not in PERIOD_STATUSES:
        raise ValidationAppError('Invalid period status.')
    if payload.end_date < payload.start_date:
        raise ValidationAppError('endDate must be on or after startDate.')
    code = payload.code.strip()
    if db.execute(select(ReportingPeriod.id).where(ReportingPeriod.organization_id == organization_id, ReportingPeriod.code == code)).scalar_one_or_none():
        raise ConflictError('Reporting period code already exists.')
    _ensure_no_same_type_overlap(db, organization_id, payload.period_type, payload.start_date, payload.end_date)
    period = ReportingPeriod(organization_id=organization_id, code=code, name=payload.name.strip(), period_type=payload.period_type, start_date=payload.start_date, end_date=payload.end_date, status=payload.status)
    db.add(period)
    db.flush()
    write_audit_log(db, action='reporting_period.created', actor_user_id=user.id, organization_id=organization_id, entity_type='reporting_period', entity_id=str(period.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': code})
    db.commit()
    db.refresh(period)
    resp = PeriodResponse.model_validate(period)
    resp.activity_record_count = 0
    return resp

def update_period(db: Session, user: User, organization_id: uuid.UUID, period_id: uuid.UUID, payload: PeriodUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PeriodResponse:
    require_period_manage(db, user, organization_id)
    period = get_period(db, organization_id, period_id)
    if period.status == 'locked':
        raise BusinessRuleError('Locked reporting periods cannot be edited.')
    data = payload.model_dump(exclude_unset=True)
    start = data.get('start_date', period.start_date)
    end = data.get('end_date', period.end_date)
    if end < start:
        raise ValidationAppError('endDate must be on or after startDate.')
    _ensure_no_same_type_overlap(db, organization_id, period.period_type, start, end, exclude_id=period.id)
    for key, value in data.items():
        setattr(period, key, value)
    write_audit_log(db, action='reporting_period.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='reporting_period', entity_id=str(period.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fields': list(data.keys())})
    db.commit()
    db.refresh(period)
    return PeriodResponse.model_validate(period)

def lock_period(db: Session, user: User, organization_id: uuid.UUID, period_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PeriodResponse:
    require_period_lock(db, user, organization_id)
    period = get_period(db, organization_id, period_id)
    if period.status == 'locked':
        raise BusinessRuleError('Reporting period is already locked.')
    if period.status == 'archived':
        raise BusinessRuleError('Archived periods cannot be locked.')
    period.status = 'locked'
    period.locked_at = datetime.now(UTC)
    period.locked_by_user_id = user.id
    write_audit_log(db, action='reporting_period.locked', actor_user_id=user.id, organization_id=organization_id, entity_type='reporting_period', entity_id=str(period.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(period)
    return PeriodResponse.model_validate(period)

def unlock_period(db: Session, user: User, organization_id: uuid.UUID, period_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PeriodResponse:
    require_period_unlock(db, user, organization_id)
    period = get_period(db, organization_id, period_id)
    if period.status != 'locked':
        raise BusinessRuleError('Only locked periods can be unlocked.')
    period.status = 'open'
    period.locked_at = None
    period.locked_by_user_id = None
    write_audit_log(db, action='reporting_period.unlocked', actor_user_id=user.id, organization_id=organization_id, entity_type='reporting_period', entity_id=str(period.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(period)
    return PeriodResponse.model_validate(period)

def archive_period(db: Session, user: User, organization_id: uuid.UUID, period_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> PeriodResponse:
    require_period_manage(db, user, organization_id)
    period = get_period(db, organization_id, period_id)
    period.status = 'archived'
    write_audit_log(db, action='reporting_period.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='reporting_period', entity_id=str(period.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(period)
    return PeriodResponse.model_validate(period)

def assert_period_writable(period: ReportingPeriod) -> None:
    if period.status == 'locked':
        raise BusinessRuleError('Reporting period is locked.')
    if period.status == 'archived':
        raise BusinessRuleError('Reporting period is archived.')
