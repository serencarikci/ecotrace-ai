from __future__ import annotations
import re
import uuid
from datetime import date
from decimal import Decimal
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.ops_constants import FACILITY_TYPES
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_manage_structure
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate
TZ_RE = re.compile('^[A-Za-z0-9_+\\-/]+$')

class FacilityCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    facility_type: str
    country_code: str
    city: str | None = None
    district: str | None = None
    address_line: str | None = None
    postal_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    timezone: str = 'UTC'
    operational_start_date: date | None = None
    operational_end_date: date | None = None
    is_active: bool = True

class FacilityUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    facility_type: str | None = None
    country_code: str | None = None
    city: str | None = None
    district: str | None = None
    address_line: str | None = None
    postal_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    timezone: str | None = None
    operational_start_date: date | None = None
    operational_end_date: date | None = None
    is_active: bool | None = None

class FacilityResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    facility_type: str
    country_code: str
    city: str | None
    district: str | None
    address_line: str | None
    postal_code: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    timezone: str
    operational_start_date: date | None
    operational_end_date: date | None
    is_active: bool

def _validate_facility_fields(*, facility_type: str, country_code: str, timezone: str, latitude: Decimal | None, longitude: Decimal | None, start: date | None, end: date | None) -> None:
    if facility_type not in FACILITY_TYPES:
        raise ValidationAppError('Invalid facility type.', details=[{'field': 'facilityType', 'message': 'Unknown facility type code.'}])
    code = country_code.strip().upper()
    if len(code) != 2 or not code.isalpha():
        raise ValidationAppError('Invalid country code.', details=[{'field': 'countryCode', 'message': 'Must be ISO 3166-1 alpha-2.'}])
    if not TZ_RE.match(timezone.strip()):
        raise ValidationAppError('Invalid timezone.', details=[{'field': 'timezone', 'message': 'Use an IANA-like timezone id.'}])
    if latitude is not None and (latitude < -90 or latitude > 90):
        raise ValidationAppError('Latitude out of range.')
    if longitude is not None and (longitude < -180 or longitude > 180):
        raise ValidationAppError('Longitude out of range.')
    if start and end and (end < start):
        raise ValidationAppError('Operational end date cannot be earlier than start date.')

def _to_response(f: Facility) -> FacilityResponse:
    return FacilityResponse.model_validate(f)

def get_facility(db: Session, organization_id: uuid.UUID, facility_id: uuid.UUID) -> Facility:
    facility = db.get(Facility, facility_id)
    if facility is None or facility.organization_id != organization_id:
        raise NotFoundError('Facility not found.')
    return facility

def list_facilities(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, search: str | None=None, facility_type: str | None=None, country_code: str | None=None, city: str | None=None, is_active: bool | None=None) -> Page[FacilityResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(Facility).where(Facility.organization_id == organization_id)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(Facility.name.ilike(like), Facility.code.ilike(like)))
    if facility_type:
        stmt = stmt.where(Facility.facility_type == facility_type)
    if country_code:
        stmt = stmt.where(Facility.country_code == country_code.upper())
    if city:
        stmt = stmt.where(Facility.city.ilike(f'%{city.strip()}%'))
    if is_active is not None:
        stmt = stmt.where(Facility.is_active.is_(is_active))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(Facility.name.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_facility(db: Session, user: User, organization_id: uuid.UUID, payload: FacilityCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FacilityResponse:
    require_manage_structure(db, user, organization_id)
    _validate_facility_fields(facility_type=payload.facility_type, country_code=payload.country_code, timezone=payload.timezone, latitude=payload.latitude, longitude=payload.longitude, start=payload.operational_start_date, end=payload.operational_end_date)
    code = payload.code.strip()
    if not code or not payload.name.strip():
        raise ValidationAppError('Code and name are required.')
    exists = db.execute(select(Facility.id).where(Facility.organization_id == organization_id, Facility.code == code)).scalar_one_or_none()
    if exists:
        raise ConflictError('A facility with this code already exists in the organization.')
    facility = Facility(organization_id=organization_id, code=code, name=payload.name.strip(), description=payload.description, facility_type=payload.facility_type, country_code=payload.country_code.strip().upper(), city=payload.city, district=payload.district, address_line=payload.address_line, postal_code=payload.postal_code, latitude=payload.latitude, longitude=payload.longitude, timezone=payload.timezone.strip(), operational_start_date=payload.operational_start_date, operational_end_date=payload.operational_end_date, is_active=payload.is_active)
    db.add(facility)
    db.flush()
    write_audit_log(db, action='facility.created', actor_user_id=user.id, organization_id=organization_id, entity_type='facility', entity_id=str(facility.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': facility.code})
    db.commit()
    db.refresh(facility)
    return _to_response(facility)

def update_facility(db: Session, user: User, organization_id: uuid.UUID, facility_id: uuid.UUID, payload: FacilityUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FacilityResponse:
    require_manage_structure(db, user, organization_id)
    facility = get_facility(db, organization_id, facility_id)
    data = payload.model_dump(exclude_unset=True)
    merged_type = data.get('facility_type', facility.facility_type)
    merged_country = data.get('country_code', facility.country_code)
    merged_tz = data.get('timezone', facility.timezone)
    merged_lat = data.get('latitude', facility.latitude)
    merged_lon = data.get('longitude', facility.longitude)
    merged_start = data.get('operational_start_date', facility.operational_start_date)
    merged_end = data.get('operational_end_date', facility.operational_end_date)
    _validate_facility_fields(facility_type=merged_type, country_code=merged_country, timezone=merged_tz, latitude=merged_lat, longitude=merged_lon, start=merged_start, end=merged_end)
    if data.get('country_code'):
        data['country_code'] = data['country_code'].strip().upper()
    for key, value in data.items():
        setattr(facility, key, value)
    write_audit_log(db, action='facility.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='facility', entity_id=str(facility.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fields': list(data.keys())})
    db.commit()
    db.refresh(facility)
    return _to_response(facility)

def archive_facility(db: Session, user: User, organization_id: uuid.UUID, facility_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FacilityResponse:
    require_manage_structure(db, user, organization_id)
    facility = get_facility(db, organization_id, facility_id)
    facility.is_active = False
    write_audit_log(db, action='facility.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='facility', entity_id=str(facility.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(facility)
    return _to_response(facility)

def get_facility_detail(db: Session, user: User, organization_id: uuid.UUID, facility_id: uuid.UUID) -> FacilityResponse:
    ensure_org_access(db, user, organization_id)
    return _to_response(get_facility(db, organization_id, facility_id))
