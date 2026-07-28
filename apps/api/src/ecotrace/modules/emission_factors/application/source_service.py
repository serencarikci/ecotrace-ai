from __future__ import annotations
import uuid
from datetime import date
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.modules.emission_factors.infrastructure.models import EmissionFactorSource
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import require_system_admin
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class FactorSourceCreate(CamelModel):
    code: str
    name: str
    publisher: str | None = None
    description: str | None = None
    source_url: str | None = None
    methodology: str | None = None
    geographic_coverage: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    release_version: str | None = None
    published_at: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    is_demo: bool = True

class FactorSourceUpdate(CamelModel):
    name: str | None = None
    publisher: str | None = None
    description: str | None = None
    source_url: str | None = None
    methodology: str | None = None
    geographic_coverage: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    release_version: str | None = None
    published_at: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    is_active: bool | None = None

class FactorSourceResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    publisher: str | None
    description: str | None
    source_url: str | None
    methodology: str | None
    geographic_coverage: str | None
    license_name: str | None
    license_url: str | None
    release_version: str | None
    published_at: date | None
    valid_from: date | None
    valid_to: date | None
    is_active: bool
    is_demo: bool

def _to_response(row: EmissionFactorSource) -> FactorSourceResponse:
    return FactorSourceResponse.model_validate(row)

def list_sources(db: Session, user: User, *, page: int=1, page_size: int=20, active_only: bool=False, search: str | None=None) -> Page[FactorSourceResponse]:
    _ = user
    stmt = select(EmissionFactorSource)
    count_stmt = select(func.count()).select_from(EmissionFactorSource)
    if active_only:
        stmt = stmt.where(EmissionFactorSource.is_active.is_(True))
        count_stmt = count_stmt.where(EmissionFactorSource.is_active.is_(True))
    if search:
        pattern = f'%{search.strip()}%'
        filt = or_(EmissionFactorSource.code.ilike(pattern), EmissionFactorSource.name.ilike(pattern), EmissionFactorSource.publisher.ilike(pattern))
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)
    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(EmissionFactorSource.code).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return paginate([_to_response(r) for r in rows], page=page, page_size=page_size, total_items=total)

def get_source(db: Session, user: User, source_id: uuid.UUID) -> FactorSourceResponse:
    _ = user
    row = db.get(EmissionFactorSource, source_id)
    if row is None:
        raise NotFoundError('Emission factor source not found.')
    return _to_response(row)

def create_source(db: Session, user: User, payload: FactorSourceCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorSourceResponse:
    require_system_admin(user, message='Only system administrators may manage factor sources.')
    code = payload.code.strip()
    if not code:
        raise ValidationAppError('Code is required.')
    existing = db.execute(select(EmissionFactorSource).where(EmissionFactorSource.code == code)).scalar_one_or_none()
    if existing:
        raise ConflictError('Emission factor source code already exists.')
    if payload.valid_from and payload.valid_to and (payload.valid_to < payload.valid_from):
        raise ValidationAppError('validTo must not be earlier than validFrom.')
    row = EmissionFactorSource(code=code, name=payload.name.strip(), publisher=payload.publisher, description=payload.description, source_url=payload.source_url, methodology=payload.methodology, geographic_coverage=payload.geographic_coverage, license_name=payload.license_name, license_url=payload.license_url, release_version=payload.release_version, published_at=payload.published_at, valid_from=payload.valid_from, valid_to=payload.valid_to, is_active=True, is_demo=payload.is_demo)
    db.add(row)
    db.flush()
    write_audit_log(db, action='factor_source.created', actor_user_id=user.id, entity_type='emission_factor_source', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': row.code})
    db.commit()
    db.refresh(row)
    return _to_response(row)

def update_source(db: Session, user: User, source_id: uuid.UUID, payload: FactorSourceUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorSourceResponse:
    require_system_admin(user, message='Only system administrators may manage factor sources.')
    row = db.get(EmissionFactorSource, source_id)
    if row is None:
        raise NotFoundError('Emission factor source not found.')
    data = payload.model_dump(exclude_unset=True)
    valid_from = data.get('valid_from', row.valid_from)
    valid_to = data.get('valid_to', row.valid_to)
    if valid_from and valid_to and (valid_to < valid_from):
        raise ValidationAppError('validTo must not be earlier than validFrom.')
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='factor_source.updated', actor_user_id=user.id, entity_type='emission_factor_source', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'fields': list(data.keys())})
    db.commit()
    db.refresh(row)
    return _to_response(row)

def archive_source(db: Session, user: User, source_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FactorSourceResponse:
    require_system_admin(user, message='Only system administrators may manage factor sources.')
    row = db.get(EmissionFactorSource, source_id)
    if row is None:
        raise NotFoundError('Emission factor source not found.')
    row.is_active = False
    write_audit_log(db, action='factor_source.archived', actor_user_id=user.id, entity_type='emission_factor_source', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return _to_response(row)
