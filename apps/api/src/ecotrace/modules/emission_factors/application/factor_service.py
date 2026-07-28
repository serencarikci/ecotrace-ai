from __future__ import annotations
import uuid
from datetime import date
from decimal import Decimal
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.carbon_constants import SCOPES
from ecotrace.core.constants import ROLE_SYSTEM_ADMIN
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.carbon_accounting.application.matching_service import find_overlapping_active_factors
from ecotrace.modules.carbon_inventory.infrastructure.models import CarbonCalculationItem
from ecotrace.modules.emission_factors.infrastructure.models import EmissionFactor, EmissionFactorSource
from ecotrace.modules.identity.application.auth_service import user_has_role
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.reference_data.infrastructure.models import ActivityType, Unit
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_system_admin
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class FactorCreate(CamelModel):
    source_id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    activity_type_id: uuid.UUID
    scope: str
    category: str
    subcategory: str | None = None
    geography_code: str = 'GLOBAL'
    facility_type: str | None = None
    technology_code: str | None = None
    fuel_type: str | None = None
    transportation_mode: str | None = None
    vehicle_type: str | None = None
    unit_code: str
    factor_value: Decimal | None = None
    co2_factor: Decimal | None = None
    ch4_factor: Decimal | None = None
    n2o_factor: Decimal | None = None
    other_gases_json: dict[str, Any] | None = None
    biogenic_co2_factor: Decimal | None = None
    uncertainty_percentage: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    version: int = 1
    metadata_json: dict[str, Any] | None = None
    is_demo: bool = True

class FactorUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    scope: str | None = None
    category: str | None = None
    subcategory: str | None = None
    geography_code: str | None = None
    facility_type: str | None = None
    technology_code: str | None = None
    fuel_type: str | None = None
    transportation_mode: str | None = None
    vehicle_type: str | None = None
    unit_code: str | None = None
    factor_value: Decimal | None = None
    co2_factor: Decimal | None = None
    ch4_factor: Decimal | None = None
    n2o_factor: Decimal | None = None
    other_gases_json: dict[str, Any] | None = None
    biogenic_co2_factor: Decimal | None = None
    uncertainty_percentage: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    metadata_json: dict[str, Any] | None = None

class FactorResponse(CamelModel):
    id: uuid.UUID
    source_id: uuid.UUID
    code: str
    name: str
    description: str | None
    activity_type_id: uuid.UUID
    scope: str
    category: str
    subcategory: str | None
    geography_code: str
    facility_type: str | None
    technology_code: str | None
    fuel_type: str | None
    transportation_mode: str | None
    vehicle_type: str | None
    unit_code: str
    factor_value: Decimal | None
    co2_factor: Decimal | None
    ch4_factor: Decimal | None
    n2o_factor: Decimal | None
    other_gases_json: dict[str, Any] | None
    biogenic_co2_factor: Decimal | None
    uncertainty_percentage: Decimal | None
    valid_from: date | None
    valid_to: date | None
    version: int
    status: str
    is_active: bool
    is_demo: bool
    supersedes_factor_id: uuid.UUID | None
    metadata_json: dict[str, Any] | None
    usage_count: int = 0

def _validate_factor_values(payload: FactorCreate | FactorUpdate | dict[str, Any]) -> None:
    data = payload if isinstance(payload, dict) else payload.model_dump(exclude_unset=False)
    for field in ('factor_value', 'co2_factor', 'ch4_factor', 'n2o_factor', 'biogenic_co2_factor'):
        value = data.get(field)
        if value is not None and Decimal(str(value)) < 0:
            raise ValidationAppError(f'{field} must be non-negative.')
    unc = data.get('uncertainty_percentage')
    if unc is not None and (Decimal(str(unc)) < 0 or Decimal(str(unc)) > 100):
        raise ValidationAppError('uncertaintyPercentage must be between 0 and 100.')
    vf = data.get('valid_from')
    vt = data.get('valid_to')
    if vf and vt and (vt < vf):
        raise ValidationAppError('validTo must not be earlier than validFrom.')
    has_aggregate = data.get('factor_value') is not None
    has_gas = any((data.get(f) is not None for f in ('co2_factor', 'ch4_factor', 'n2o_factor')))
    if not has_aggregate and (not has_gas):
        raise ValidationAppError('Provide factorValue and/or gas-specific factors.')

def _ensure_unit_compatible(db: Session, unit_code: str, activity_type_id: uuid.UUID) -> None:
    activity_type = db.get(ActivityType, activity_type_id)
    if activity_type is None:
        raise ValidationAppError('Unknown activity type.')
    unit = db.execute(select(Unit).where(Unit.code == unit_code, Unit.is_active.is_(True))).scalar_one_or_none()
    if unit is None:
        raise ValidationAppError('Unknown or inactive unit.')
    if unit.dimension != activity_type.allowed_unit_dimension:
        raise ValidationAppError('Factor unit is not compatible with the activity type.')

def _to_response(db: Session, row: EmissionFactor) -> FactorResponse:
    usage = db.execute(select(func.count()).select_from(CarbonCalculationItem).where(CarbonCalculationItem.emission_factor_id == row.id)).scalar_one()
    data = FactorResponse.model_validate(row)
    data.usage_count = usage
    return data

def list_factors(db: Session, user: User, *, page: int=1, page_size: int=20, source_id: uuid.UUID | None=None, activity_type_id: uuid.UUID | None=None, scope: str | None=None, category: str | None=None, geography_code: str | None=None, status: str | None=None, valid_on: date | None=None, search: str | None=None, include_drafts: bool=False) -> Page[FactorResponse]:
    is_admin = user_has_role(user, ROLE_SYSTEM_ADMIN)
    stmt = select(EmissionFactor)
    count_stmt = select(func.count()).select_from(EmissionFactor)
    if not is_admin or not include_drafts:
        filt = EmissionFactor.status.in_(['active', 'superseded', 'archived'])
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    if source_id:
        stmt = stmt.where(EmissionFactor.source_id == source_id)
        count_stmt = count_stmt.where(EmissionFactor.source_id == source_id)
    if activity_type_id:
        stmt = stmt.where(EmissionFactor.activity_type_id == activity_type_id)
        count_stmt = count_stmt.where(EmissionFactor.activity_type_id == activity_type_id)
    if scope:
        stmt = stmt.where(EmissionFactor.scope == scope)
        count_stmt = count_stmt.where(EmissionFactor.scope == scope)
    if category:
        stmt = stmt.where(EmissionFactor.category == category)
        count_stmt = count_stmt.where(EmissionFactor.category == category)
    if geography_code:
        stmt = stmt.where(EmissionFactor.geography_code == geography_code.upper())
        count_stmt = count_stmt.where(EmissionFactor.geography_code == geography_code.upper())
    if status:
        stmt = stmt.where(EmissionFactor.status == status)
        count_stmt = count_stmt.where(EmissionFactor.status == status)
    if valid_on:
        date_filt = and_valid_on(valid_on)
        stmt = stmt.where(date_filt)
        count_stmt = count_stmt.where(date_filt)
    if search:
        pattern = f'%{search.strip()}%'
        sfilt = or_(EmissionFactor.code.ilike(pattern), EmissionFactor.name.ilike(pattern))
        stmt = stmt.where(sfilt)
        count_stmt = count_stmt.where(sfilt)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(EmissionFactor.code, EmissionFactor.version.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_to_response(db, r) for r in rows], page=page, page_size=page_size, total_items=total)

def and_valid_on(valid_on: date) -> Any:
    return (EmissionFactor.valid_from.is_(None) | (EmissionFactor.valid_from <= valid_on)) & (EmissionFactor.valid_to.is_(None) | (EmissionFactor.valid_to >= valid_on))

def get_factor(db: Session, user: User, factor_id: uuid.UUID) -> FactorResponse:
    row = db.get(EmissionFactor, factor_id)
    if row is None:
        raise NotFoundError('Emission factor not found.')
    if row.status == 'draft' and (not user_has_role(user, ROLE_SYSTEM_ADMIN)):
        raise NotFoundError('Emission factor not found.')
    return _to_response(db, row)

def create_draft(db: Session, user: User, payload: FactorCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorResponse:
    require_system_admin(user, message='Only system administrators may mutate emission factors.')
    _validate_factor_values(payload)
    if payload.scope not in SCOPES:
        raise ValidationAppError('Invalid scope.')
    source = db.get(EmissionFactorSource, payload.source_id)
    if source is None:
        raise ValidationAppError('Unknown emission factor source.')
    _ensure_unit_compatible(db, payload.unit_code, payload.activity_type_id)
    code = payload.code.strip()
    existing = db.execute(select(EmissionFactor).where(EmissionFactor.code == code, EmissionFactor.version == payload.version)).scalar_one_or_none()
    if existing:
        raise ConflictError('Factor code and version combination already exists.')
    row = EmissionFactor(source_id=payload.source_id, code=code, name=payload.name.strip(), description=payload.description, activity_type_id=payload.activity_type_id, scope=payload.scope, category=payload.category, subcategory=payload.subcategory, geography_code=(payload.geography_code or 'GLOBAL').upper(), facility_type=payload.facility_type, technology_code=payload.technology_code, fuel_type=payload.fuel_type, transportation_mode=payload.transportation_mode, vehicle_type=payload.vehicle_type, unit_code=payload.unit_code, factor_value=payload.factor_value, co2_factor=payload.co2_factor, ch4_factor=payload.ch4_factor, n2o_factor=payload.n2o_factor, other_gases_json=payload.other_gases_json, biogenic_co2_factor=payload.biogenic_co2_factor, uncertainty_percentage=payload.uncertainty_percentage, valid_from=payload.valid_from, valid_to=payload.valid_to, version=payload.version, status='draft', is_active=False, is_demo=payload.is_demo, metadata_json=payload.metadata_json or {'disclaimer': 'Demo/reference data — not for regulatory reporting.'})
    db.add(row)
    db.flush()
    write_audit_log(db, action='factor.draft_created', actor_user_id=user.id, entity_type='emission_factor', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': row.code, 'version': row.version})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def update_draft(db: Session, user: User, factor_id: uuid.UUID, payload: FactorUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorResponse:
    require_system_admin(user, message='Only system administrators may mutate emission factors.')
    row = db.get(EmissionFactor, factor_id)
    if row is None:
        raise NotFoundError('Emission factor not found.')
    if row.status != 'draft':
        raise BusinessRuleError('Only draft factors may be edited. Clone a new version instead.')
    data = payload.model_dump(exclude_unset=True)
    merged = {'factor_value': data.get('factor_value', row.factor_value), 'co2_factor': data.get('co2_factor', row.co2_factor), 'ch4_factor': data.get('ch4_factor', row.ch4_factor), 'n2o_factor': data.get('n2o_factor', row.n2o_factor), 'biogenic_co2_factor': data.get('biogenic_co2_factor', row.biogenic_co2_factor), 'uncertainty_percentage': data.get('uncertainty_percentage', row.uncertainty_percentage), 'valid_from': data.get('valid_from', row.valid_from), 'valid_to': data.get('valid_to', row.valid_to)}
    _validate_factor_values(merged)
    if 'scope' in data and data['scope'] not in SCOPES:
        raise ValidationAppError('Invalid scope.')
    unit_code = data.get('unit_code', row.unit_code)
    _ensure_unit_compatible(db, unit_code, row.activity_type_id)
    if data.get('geography_code'):
        data['geography_code'] = data['geography_code'].upper()
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='factor.draft_updated', actor_user_id=user.id, entity_type='emission_factor', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fields': list(data.keys())})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def activate_factor(db: Session, user: User, factor_id: uuid.UUID, *, supersede_previous: bool=True, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorResponse:
    require_system_admin(user, message='Only system administrators may mutate emission factors.')
    row = db.get(EmissionFactor, factor_id)
    if row is None:
        raise NotFoundError('Emission factor not found.')
    if row.status not in {'draft', 'superseded'}:
        raise BusinessRuleError('Only draft or superseded factors can be activated.')
    overlaps = find_overlapping_active_factors(db, activity_type_id=row.activity_type_id, geography_code=row.geography_code, technology_code=row.technology_code, fuel_type=row.fuel_type, transportation_mode=row.transportation_mode, unit_code=row.unit_code, valid_from=row.valid_from, valid_to=row.valid_to, exclude_factor_id=row.id)
    previous = None
    if supersede_previous:
        previous = db.execute(select(EmissionFactor).where(EmissionFactor.code == row.code, EmissionFactor.status == 'active', EmissionFactor.id != row.id)).scalar_one_or_none()
        if previous:
            previous.status = 'superseded'
            previous.is_active = False
            row.supersedes_factor_id = previous.id
            overlaps = [o for o in overlaps if o.id != previous.id]
    if overlaps:
        raise ConflictError('Activating this factor would create an ambiguous overlap with other active factors.', details=[{'factorId': str(o.id), 'code': o.code, 'version': o.version} for o in overlaps])
    row.status = 'active'
    row.is_active = True
    write_audit_log(db, action='factor.activated', actor_user_id=user.id, entity_type='emission_factor', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': row.code, 'version': row.version, 'supersededId': str(previous.id) if previous else None})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def supersede_factor(db: Session, user: User, factor_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorResponse:
    require_system_admin(user, message='Only system administrators may mutate emission factors.')
    row = db.get(EmissionFactor, factor_id)
    if row is None:
        raise NotFoundError('Emission factor not found.')
    if row.status != 'active':
        raise BusinessRuleError('Only active factors can be superseded.')
    row.status = 'superseded'
    row.is_active = False
    write_audit_log(db, action='factor.superseded', actor_user_id=user.id, entity_type='emission_factor', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def archive_factor(db: Session, user: User, factor_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorResponse:
    require_system_admin(user, message='Only system administrators may mutate emission factors.')
    row = db.get(EmissionFactor, factor_id)
    if row is None:
        raise NotFoundError('Emission factor not found.')
    row.status = 'archived'
    row.is_active = False
    write_audit_log(db, action='factor.archived', actor_user_id=user.id, entity_type='emission_factor', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def clone_version(db: Session, user: User, factor_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorResponse:
    require_system_admin(user, message='Only system administrators may mutate emission factors.')
    source = db.get(EmissionFactor, factor_id)
    if source is None:
        raise NotFoundError('Emission factor not found.')
    max_version = db.execute(select(func.max(EmissionFactor.version)).where(EmissionFactor.code == source.code)).scalar_one()
    new_version = int(max_version or source.version) + 1
    row = EmissionFactor(source_id=source.source_id, code=source.code, name=source.name, description=source.description, activity_type_id=source.activity_type_id, scope=source.scope, category=source.category, subcategory=source.subcategory, geography_code=source.geography_code, facility_type=source.facility_type, technology_code=source.technology_code, fuel_type=source.fuel_type, transportation_mode=source.transportation_mode, vehicle_type=source.vehicle_type, unit_code=source.unit_code, factor_value=source.factor_value, co2_factor=source.co2_factor, ch4_factor=source.ch4_factor, n2o_factor=source.n2o_factor, other_gases_json=source.other_gases_json, biogenic_co2_factor=source.biogenic_co2_factor, uncertainty_percentage=source.uncertainty_percentage, valid_from=source.valid_from, valid_to=source.valid_to, version=new_version, status='draft', is_active=False, is_demo=source.is_demo, supersedes_factor_id=source.id, metadata_json=source.metadata_json)
    db.add(row)
    db.flush()
    write_audit_log(db, action='factor.cloned', actor_user_id=user.id, entity_type='emission_factor', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fromId': str(source.id), 'version': new_version})
    db.commit()
    db.refresh(row)
    return _to_response(db, row)

def list_versions(db: Session, user: User, factor_id: uuid.UUID) -> list[FactorResponse]:
    row = db.get(EmissionFactor, factor_id)
    if row is None:
        raise NotFoundError('Emission factor not found.')
    if row.status == 'draft' and (not user_has_role(user, ROLE_SYSTEM_ADMIN)):
        raise NotFoundError('Emission factor not found.')
    rows = db.execute(select(EmissionFactor).where(EmissionFactor.code == row.code).order_by(EmissionFactor.version.desc())).scalars().all()
    if not user_has_role(user, ROLE_SYSTEM_ADMIN):
        rows = [r for r in rows if r.status != 'draft']
    return [_to_response(db, r) for r in rows]
