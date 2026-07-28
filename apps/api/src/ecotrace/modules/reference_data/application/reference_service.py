from __future__ import annotations
import uuid
from decimal import Decimal
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.ops_constants import ACTIVITY_CATEGORIES, UNIT_DIMENSIONS
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.reference_data.infrastructure.models import ActivityType, Unit
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_system_admin
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class UnitCreate(CamelModel):
    code: str
    name: str
    symbol: str
    dimension: str
    conversion_factor_to_base: Decimal
    base_unit_code: str
    decimal_precision: int = 4
    is_active: bool = True

class UnitUpdate(CamelModel):
    name: str | None = None
    symbol: str | None = None
    dimension: str | None = None
    conversion_factor_to_base: Decimal | None = None
    base_unit_code: str | None = None
    decimal_precision: int | None = None
    is_active: bool | None = None

class UnitResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    symbol: str
    dimension: str
    conversion_factor_to_base: Decimal
    base_unit_code: str
    decimal_precision: int
    is_active: bool

class ActivityTypeCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    category: str
    default_unit_code: str
    allowed_unit_dimension: str
    expected_value_type: str = 'decimal'
    data_frequency: str = 'monthly'
    requires_facility: bool = True
    requires_equipment: bool = False
    is_active: bool = True

class ActivityTypeUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    default_unit_code: str | None = None
    allowed_unit_dimension: str | None = None
    expected_value_type: str | None = None
    data_frequency: str | None = None
    requires_facility: bool | None = None
    requires_equipment: bool | None = None
    is_active: bool | None = None

class ActivityTypeResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    category: str
    default_unit_code: str
    allowed_unit_dimension: str
    expected_value_type: str
    data_frequency: str
    requires_facility: bool
    requires_equipment: bool
    is_active: bool

def _validate_unit_fields(*, dimension: str, conversion_factor: Decimal, decimal_precision: int) -> None:
    if dimension not in UNIT_DIMENSIONS:
        raise ValidationAppError('Invalid unit dimension.', details=[{'field': 'dimension', 'message': 'Unknown dimension code.'}])
    if conversion_factor <= 0:
        raise ValidationAppError('Conversion factor must be positive.')
    if decimal_precision < 0:
        raise ValidationAppError('Decimal precision cannot be negative.')

def _validate_activity_type_fields(db: Session, *, category: str, default_unit_code: str, allowed_unit_dimension: str) -> None:
    if category not in ACTIVITY_CATEGORIES:
        raise ValidationAppError('Invalid activity category.', details=[{'field': 'category', 'message': 'Unknown category code.'}])
    if allowed_unit_dimension not in UNIT_DIMENSIONS:
        raise ValidationAppError('Invalid allowed unit dimension.')
    unit = db.execute(select(Unit).where(Unit.code == default_unit_code, Unit.is_active.is_(True))).scalar_one_or_none()
    if unit is None:
        raise ValidationAppError('Default unit not found or inactive.', details=[{'field': 'defaultUnitCode', 'message': 'Unknown unit.'}])
    if unit.dimension != allowed_unit_dimension:
        raise ValidationAppError('Default unit dimension must match allowed unit dimension.')

def list_units(db: Session, user: User, *, page: int, page_size: int, active_only: bool=True, dimension: str | None=None, search: str | None=None) -> Page[UnitResponse]:
    _ = user
    stmt = select(Unit)
    if active_only:
        stmt = stmt.where(Unit.is_active.is_(True))
    if dimension:
        stmt = stmt.where(Unit.dimension == dimension)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(Unit.code.ilike(like), Unit.name.ilike(like), Unit.symbol.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(Unit.code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([UnitResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_unit(db: Session, user: User, payload: UnitCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> UnitResponse:
    require_system_admin(user)
    code = payload.code.strip()
    if not code or not payload.name.strip() or (not payload.symbol.strip()):
        raise ValidationAppError('Code, name, and symbol are required.')
    _validate_unit_fields(dimension=payload.dimension, conversion_factor=payload.conversion_factor_to_base, decimal_precision=payload.decimal_precision)
    exists = db.execute(select(Unit.id).where(Unit.code == code)).scalar_one_or_none()
    if exists:
        raise ConflictError('A unit with this code already exists.')
    unit = Unit(code=code, name=payload.name.strip(), symbol=payload.symbol.strip(), dimension=payload.dimension, conversion_factor_to_base=payload.conversion_factor_to_base, base_unit_code=payload.base_unit_code.strip(), decimal_precision=payload.decimal_precision, is_active=payload.is_active)
    db.add(unit)
    db.flush()
    write_audit_log(db, action='unit.created', actor_user_id=user.id, entity_type='unit', entity_id=str(unit.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': unit.code})
    db.commit()
    db.refresh(unit)
    return UnitResponse.model_validate(unit)

def update_unit(db: Session, user: User, unit_id: uuid.UUID, payload: UnitUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> UnitResponse:
    require_system_admin(user)
    unit = db.get(Unit, unit_id)
    if unit is None:
        raise NotFoundError('Unit not found.')
    data = payload.model_dump(exclude_unset=True)
    dimension = data.get('dimension', unit.dimension)
    factor = data.get('conversion_factor_to_base', unit.conversion_factor_to_base)
    precision = data.get('decimal_precision', unit.decimal_precision)
    _validate_unit_fields(dimension=dimension, conversion_factor=factor, decimal_precision=precision)
    for key, value in data.items():
        setattr(unit, key, value)
    write_audit_log(db, action='unit.updated', actor_user_id=user.id, entity_type='unit', entity_id=str(unit.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fields': list(data.keys())})
    db.commit()
    db.refresh(unit)
    return UnitResponse.model_validate(unit)

def list_activity_types(db: Session, user: User, *, page: int, page_size: int, active_only: bool=True, category: str | None=None, search: str | None=None) -> Page[ActivityTypeResponse]:
    _ = user
    stmt = select(ActivityType)
    if active_only:
        stmt = stmt.where(ActivityType.is_active.is_(True))
    if category:
        stmt = stmt.where(ActivityType.category == category)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(ActivityType.code.ilike(like), ActivityType.name.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(ActivityType.code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([ActivityTypeResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_activity_type(db: Session, user: User, payload: ActivityTypeCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ActivityTypeResponse:
    require_system_admin(user)
    code = payload.code.strip()
    if not code or not payload.name.strip():
        raise ValidationAppError('Code and name are required.')
    _validate_activity_type_fields(db, category=payload.category, default_unit_code=payload.default_unit_code.strip(), allowed_unit_dimension=payload.allowed_unit_dimension)
    exists = db.execute(select(ActivityType.id).where(ActivityType.code == code)).scalar_one_or_none()
    if exists:
        raise ConflictError('An activity type with this code already exists.')
    activity_type = ActivityType(code=code, name=payload.name.strip(), description=payload.description, category=payload.category, default_unit_code=payload.default_unit_code.strip(), allowed_unit_dimension=payload.allowed_unit_dimension, expected_value_type=payload.expected_value_type, data_frequency=payload.data_frequency, requires_facility=payload.requires_facility, requires_equipment=payload.requires_equipment, is_active=payload.is_active)
    db.add(activity_type)
    db.flush()
    write_audit_log(db, action='activity_type.created', actor_user_id=user.id, entity_type='activity_type', entity_id=str(activity_type.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': activity_type.code})
    db.commit()
    db.refresh(activity_type)
    return ActivityTypeResponse.model_validate(activity_type)

def update_activity_type(db: Session, user: User, activity_type_id: uuid.UUID, payload: ActivityTypeUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ActivityTypeResponse:
    require_system_admin(user)
    activity_type = db.get(ActivityType, activity_type_id)
    if activity_type is None:
        raise NotFoundError('Activity type not found.')
    data = payload.model_dump(exclude_unset=True)
    category = data.get('category', activity_type.category)
    default_unit = data.get('default_unit_code', activity_type.default_unit_code)
    dimension = data.get('allowed_unit_dimension', activity_type.allowed_unit_dimension)
    _validate_activity_type_fields(db, category=category, default_unit_code=default_unit, allowed_unit_dimension=dimension)
    for key, value in data.items():
        setattr(activity_type, key, value)
    write_audit_log(db, action='activity_type.updated', actor_user_id=user.id, entity_type='activity_type', entity_id=str(activity_type.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fields': list(data.keys())})
    db.commit()
    db.refresh(activity_type)
    return ActivityTypeResponse.model_validate(activity_type)
