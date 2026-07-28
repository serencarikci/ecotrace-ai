from __future__ import annotations
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.lca_constants import MATERIAL_CATEGORIES
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.materials.infrastructure.models import Material
from ecotrace.modules.products.application.validators import require_non_negative, require_percentage
from ecotrace.modules.reference_data.application.unit_conversion import get_unit
from ecotrace.modules.suppliers.application.supplier_service import get_supplier
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_product_manage, require_product_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class MaterialCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    material_category: str
    default_unit_code: str
    density_value: Decimal | None = None
    density_unit: str | None = None
    recycled_content_percentage: Decimal | None = None
    renewable_content_percentage: Decimal | None = None
    hazardous: bool = False
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    metadata_json: dict[str, Any] | None = None
    is_active: bool = True

class MaterialUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    material_category: str | None = None
    default_unit_code: str | None = None
    density_value: Decimal | None = None
    density_unit: str | None = None
    recycled_content_percentage: Decimal | None = None
    renewable_content_percentage: Decimal | None = None
    hazardous: bool | None = None
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    metadata_json: dict[str, Any] | None = None
    is_active: bool | None = None

class MaterialResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    material_category: str
    default_unit_code: str
    density_value: Decimal | None
    density_unit: str | None
    recycled_content_percentage: Decimal | None
    renewable_content_percentage: Decimal | None
    hazardous: bool
    supplier_id: uuid.UUID | None
    country_of_origin: str | None
    metadata_json: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

def _validate(db: Session, organization_id: uuid.UUID, *, category: str, unit_code: str, recycled: Decimal | None, renewable: Decimal | None, density: Decimal | None, supplier_id: uuid.UUID | None, country: str | None) -> None:
    if category not in MATERIAL_CATEGORIES:
        raise ValidationAppError('Invalid material category.')
    get_unit(db, unit_code)
    require_percentage(recycled, 'recycledContentPercentage')
    require_percentage(renewable, 'renewableContentPercentage')
    require_non_negative(density, 'densityValue')
    if country and (len(country) != 2 or not country.isalpha()):
        raise ValidationAppError('Invalid country of origin.')
    if supplier_id is not None:
        get_supplier(db, organization_id, supplier_id)

def get_material(db: Session, organization_id: uuid.UUID, material_id: uuid.UUID) -> Material:
    row = db.get(Material, material_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Material not found.')
    return row

def list_materials(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, search: str | None=None, material_category: str | None=None, is_active: bool | None=None) -> Page[MaterialResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(Material).where(Material.organization_id == organization_id)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(Material.name.ilike(like), Material.code.ilike(like)))
    if material_category:
        stmt = stmt.where(Material.material_category == material_category)
    if is_active is not None:
        stmt = stmt.where(Material.is_active.is_(is_active))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(Material.code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([MaterialResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_material(db: Session, user: User, organization_id: uuid.UUID, payload: MaterialCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> MaterialResponse:
    require_product_write(db, user, organization_id)
    code = payload.code.strip()
    country = payload.country_of_origin.upper() if payload.country_of_origin else None
    _validate(db, organization_id, category=payload.material_category, unit_code=payload.default_unit_code, recycled=payload.recycled_content_percentage, renewable=payload.renewable_content_percentage, density=payload.density_value, supplier_id=payload.supplier_id, country=country)
    if db.execute(select(Material.id).where(Material.organization_id == organization_id, Material.code == code)).scalar_one_or_none():
        raise ConflictError('Material code already exists in this organization.')
    row = Material(organization_id=organization_id, code=code, name=payload.name.strip(), description=payload.description, material_category=payload.material_category, default_unit_code=payload.default_unit_code, density_value=payload.density_value, density_unit=payload.density_unit, recycled_content_percentage=payload.recycled_content_percentage, renewable_content_percentage=payload.renewable_content_percentage, hazardous=payload.hazardous, supplier_id=payload.supplier_id, country_of_origin=country, metadata_json=payload.metadata_json, is_active=payload.is_active)
    db.add(row)
    db.flush()
    write_audit_log(db, action='material.created', actor_user_id=user.id, organization_id=organization_id, entity_type='material', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': row.code})
    db.commit()
    db.refresh(row)
    return MaterialResponse.model_validate(row)

def update_material(db: Session, user: User, organization_id: uuid.UUID, material_id: uuid.UUID, payload: MaterialUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> MaterialResponse:
    require_product_write(db, user, organization_id)
    row = get_material(db, organization_id, material_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get('country_of_origin'):
        data['country_of_origin'] = data['country_of_origin'].upper()
    _validate(db, organization_id, category=data.get('material_category', row.material_category), unit_code=data.get('default_unit_code', row.default_unit_code), recycled=data.get('recycled_content_percentage', row.recycled_content_percentage), renewable=data.get('renewable_content_percentage', row.renewable_content_percentage), density=data.get('density_value', row.density_value), supplier_id=data.get('supplier_id', row.supplier_id), country=data.get('country_of_origin', row.country_of_origin))
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='material.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='material', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return MaterialResponse.model_validate(row)

def archive_material(db: Session, user: User, organization_id: uuid.UUID, material_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> MaterialResponse:
    require_product_manage(db, user, organization_id)
    row = get_material(db, organization_id, material_id)
    row.is_active = False
    write_audit_log(db, action='material.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='material', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'isActive': False})
    db.commit()
    db.refresh(row)
    return MaterialResponse.model_validate(row)

def get_material_detail(db: Session, user: User, organization_id: uuid.UUID, material_id: uuid.UUID) -> MaterialResponse:
    ensure_org_access(db, user, organization_id)
    return MaterialResponse.model_validate(get_material(db, organization_id, material_id))
