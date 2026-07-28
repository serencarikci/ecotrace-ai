from __future__ import annotations
import re
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.lca_constants import SUPPLIER_STATUSES, SUPPLIER_TYPES
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.products.application.validators import require_sustainability_rating
from ecotrace.modules.suppliers.infrastructure.models import Supplier
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_product_manage, require_product_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate
EMAIL_RE = re.compile('^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')

class SupplierCreate(CamelModel):
    code: str
    name: str
    legal_name: str | None = None
    country_code: str | None = None
    city: str | None = None
    address_line: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    website: str | None = None
    supplier_type: str
    status: str = 'draft'
    sustainability_rating: int | None = None
    metadata_json: dict[str, Any] | None = None

class SupplierUpdate(CamelModel):
    name: str | None = None
    legal_name: str | None = None
    country_code: str | None = None
    city: str | None = None
    address_line: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    website: str | None = None
    supplier_type: str | None = None
    status: str | None = None
    sustainability_rating: int | None = None
    metadata_json: dict[str, Any] | None = None

class SupplierResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    legal_name: str | None
    country_code: str | None
    city: str | None
    address_line: str | None
    contact_name: str | None
    contact_email: str | None
    website: str | None
    supplier_type: str
    status: str
    sustainability_rating: int | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

def _validate_email_url(email: str | None, website: str | None) -> None:
    if email and (not EMAIL_RE.match(email.strip())):
        raise ValidationAppError('Invalid contact email.', details=[{'field': 'contactEmail', 'message': 'Must be a valid email.'}])
    if website:
        parsed = urlparse(website.strip())
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValidationAppError('Invalid website URL.', details=[{'field': 'website', 'message': 'Must be http(s) URL.'}])

def _validate_fields(*, supplier_type: str, status: str, country_code: str | None, email: str | None, website: str | None, rating: int | None) -> None:
    if supplier_type not in SUPPLIER_TYPES:
        raise ValidationAppError('Invalid supplier type.')
    if status not in SUPPLIER_STATUSES:
        raise ValidationAppError('Invalid supplier status.')
    if country_code and (len(country_code) != 2 or not country_code.isalpha()):
        raise ValidationAppError('Invalid country code.')
    _validate_email_url(email, website)
    require_sustainability_rating(rating)

def get_supplier(db: Session, organization_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier:
    row = db.get(Supplier, supplier_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Supplier not found.')
    return row

def list_suppliers(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, search: str | None=None, status: str | None=None, country_code: str | None=None) -> Page[SupplierResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(Supplier).where(Supplier.organization_id == organization_id)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(Supplier.name.ilike(like), Supplier.code.ilike(like)))
    if status:
        stmt = stmt.where(Supplier.status == status)
    if country_code:
        stmt = stmt.where(Supplier.country_code == country_code.upper())
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(Supplier.code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([SupplierResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_supplier(db: Session, user: User, organization_id: uuid.UUID, payload: SupplierCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> SupplierResponse:
    require_product_write(db, user, organization_id)
    code = payload.code.strip()
    country = payload.country_code.upper() if payload.country_code else None
    _validate_fields(supplier_type=payload.supplier_type, status=payload.status, country_code=country, email=payload.contact_email, website=payload.website, rating=payload.sustainability_rating)
    exists = db.execute(select(Supplier.id).where(Supplier.organization_id == organization_id, Supplier.code == code)).scalar_one_or_none()
    if exists:
        raise ConflictError('Supplier code already exists in this organization.')
    row = Supplier(organization_id=organization_id, code=code, name=payload.name.strip(), legal_name=payload.legal_name, country_code=country, city=payload.city, address_line=payload.address_line, contact_name=payload.contact_name, contact_email=payload.contact_email.strip() if payload.contact_email else None, website=payload.website.strip() if payload.website else None, supplier_type=payload.supplier_type, status=payload.status, sustainability_rating=payload.sustainability_rating, metadata_json=payload.metadata_json)
    db.add(row)
    db.flush()
    write_audit_log(db, action='supplier.created', actor_user_id=user.id, organization_id=organization_id, entity_type='supplier', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': row.code})
    db.commit()
    db.refresh(row)
    return SupplierResponse.model_validate(row)

def update_supplier(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID, payload: SupplierUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> SupplierResponse:
    require_product_write(db, user, organization_id)
    row = get_supplier(db, organization_id, supplier_id)
    if row.status == 'archived':
        raise ValidationAppError('Archived suppliers cannot be updated.')
    data = payload.model_dump(exclude_unset=True)
    supplier_type = data.get('supplier_type', row.supplier_type)
    status = data.get('status', row.status)
    country = data.get('country_code', row.country_code)
    if country:
        country = country.upper()
        data['country_code'] = country
    _validate_fields(supplier_type=supplier_type, status=status, country_code=country, email=data.get('contact_email', row.contact_email), website=data.get('website', row.website), rating=data.get('sustainability_rating', row.sustainability_rating))
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='supplier.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='supplier', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return SupplierResponse.model_validate(row)

def archive_supplier(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> SupplierResponse:
    require_product_manage(db, user, organization_id)
    row = get_supplier(db, organization_id, supplier_id)
    row.status = 'archived'
    write_audit_log(db, action='supplier.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='supplier', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'status': 'archived'})
    db.commit()
    db.refresh(row)
    return SupplierResponse.model_validate(row)

def get_supplier_detail(db: Session, user: User, organization_id: uuid.UUID, supplier_id: uuid.UUID) -> SupplierResponse:
    ensure_org_access(db, user, organization_id)
    return SupplierResponse.model_validate(get_supplier(db, organization_id, supplier_id))
