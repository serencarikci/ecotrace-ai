from __future__ import annotations
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from pydantic import Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.lca_constants import BATCH_STATUSES, BATCH_TRANSITIONS, BOM_STATUSES, PRODUCT_TYPES
from ecotrace.modules.facilities.application.facility_service import get_facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.materials.application.material_service import get_material
from ecotrace.modules.operational_assets.infrastructure.models import ProductionLine
from ecotrace.modules.products.application.validators import require_non_negative, require_percentage, require_positive, require_repairability
from ecotrace.modules.products.infrastructure.models import BillOfMaterialItem, BillOfMaterials, Product, ProductBatch, ProductVariant
from ecotrace.modules.reference_data.application.unit_conversion import get_unit
from ecotrace.modules.suppliers.application.supplier_service import get_supplier
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_product_approve, require_product_manage, require_product_write
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class ProductCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    product_type: str
    product_category: str | None = None
    brand: str | None = None
    model: str | None = None
    sku: str | None = None
    gtin: str | None = None
    country_of_origin: str | None = None
    default_unit_code: str
    weight_value: Decimal | None = None
    weight_unit_code: str | None = None
    expected_lifetime_value: Decimal | None = None
    expected_lifetime_unit: str | None = None
    recyclability_percentage: Decimal | None = None
    recycled_content_percentage: Decimal | None = None
    repairability_score: int | None = None
    metadata_json: dict[str, Any] | None = None
    is_active: bool = True

class ProductUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    product_type: str | None = None
    product_category: str | None = None
    brand: str | None = None
    model: str | None = None
    sku: str | None = None
    gtin: str | None = None
    country_of_origin: str | None = None
    default_unit_code: str | None = None
    weight_value: Decimal | None = None
    weight_unit_code: str | None = None
    expected_lifetime_value: Decimal | None = None
    expected_lifetime_unit: str | None = None
    recyclability_percentage: Decimal | None = None
    recycled_content_percentage: Decimal | None = None
    repairability_score: int | None = None
    metadata_json: dict[str, Any] | None = None
    is_active: bool | None = None

class ProductResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: str | None
    product_type: str
    product_category: str | None
    brand: str | None
    model: str | None
    sku: str | None
    gtin: str | None
    country_of_origin: str | None
    default_unit_code: str
    weight_value: Decimal | None
    weight_unit_code: str | None
    expected_lifetime_value: Decimal | None
    expected_lifetime_unit: str | None
    recyclability_percentage: Decimal | None
    recycled_content_percentage: Decimal | None
    repairability_score: int | None
    is_active: bool
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

class VariantCreate(CamelModel):
    code: str
    name: str
    sku: str | None = None
    gtin: str | None = None
    description: str | None = None
    attributes_json: dict[str, Any] | None = None
    weight_value: Decimal | None = None
    weight_unit_code: str | None = None
    is_active: bool = True

class VariantUpdate(CamelModel):
    name: str | None = None
    sku: str | None = None
    gtin: str | None = None
    description: str | None = None
    attributes_json: dict[str, Any] | None = None
    weight_value: Decimal | None = None
    weight_unit_code: str | None = None
    is_active: bool | None = None

class VariantResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID
    code: str
    name: str
    sku: str | None
    gtin: str | None
    description: str | None
    attributes_json: dict[str, Any] | None
    weight_value: Decimal | None
    weight_unit_code: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class BatchCreate(CamelModel):
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    production_line_id: uuid.UUID | None = None
    batch_code: str
    production_date: date | None = None
    expiration_date: date | None = None
    quantity: Decimal
    unit_code: str
    total_weight: Decimal | None = None
    weight_unit_code: str | None = None
    status: str = 'planned'
    traceability_reference: str | None = None
    metadata_json: dict[str, Any] | None = None

class BatchUpdate(CamelModel):
    product_variant_id: uuid.UUID | None = None
    facility_id: uuid.UUID | None = None
    production_line_id: uuid.UUID | None = None
    production_date: date | None = None
    expiration_date: date | None = None
    quantity: Decimal | None = None
    unit_code: str | None = None
    total_weight: Decimal | None = None
    weight_unit_code: str | None = None
    traceability_reference: str | None = None
    metadata_json: dict[str, Any] | None = None

class BatchTransition(CamelModel):
    status: str

class BatchResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    production_line_id: uuid.UUID | None
    batch_code: str
    production_date: date | None
    expiration_date: date | None
    quantity: Decimal
    unit_code: str
    total_weight: Decimal | None
    weight_unit_code: str | None
    status: str
    traceability_reference: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

class BomItemCreate(CamelModel):
    material_id: uuid.UUID | None = None
    component_product_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    quantity: Decimal
    unit_code: str
    waste_percentage: Decimal | None = None
    recycled_content_percentage: Decimal | None = None
    source_country_code: str | None = None
    transport_distance_km: Decimal | None = None
    transport_mode: str | None = None
    allocation_percentage: Decimal | None = None
    notes: str | None = None
    metadata_json: dict[str, Any] | None = None

class BomCreate(CamelModel):
    product_variant_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    items: list[BomItemCreate] = Field(default_factory=list)

class BomUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    items: list[BomItemCreate] | None = None

class BomItemResponse(CamelModel):
    id: uuid.UUID
    bill_of_material_id: uuid.UUID
    material_id: uuid.UUID | None
    component_product_id: uuid.UUID | None
    supplier_id: uuid.UUID | None
    quantity: Decimal
    unit_code: str
    waste_percentage: Decimal | None
    recycled_content_percentage: Decimal | None
    source_country_code: str | None
    transport_distance_km: Decimal | None
    transport_mode: str | None
    allocation_percentage: Decimal | None
    notes: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

class BomResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None
    version: int
    name: str
    description: str | None
    status: str
    valid_from: date | None
    valid_to: date | None
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    items: list[BomItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

def _validate_product_fields(db: Session, *, product_type: str, unit_code: str, weight: Decimal | None, recyclability: Decimal | None, recycled: Decimal | None, repairability: int | None, country: str | None) -> None:
    if product_type not in PRODUCT_TYPES:
        raise ValidationAppError('Invalid product type.')
    get_unit(db, unit_code)
    require_non_negative(weight, 'weightValue')
    require_percentage(recyclability, 'recyclabilityPercentage')
    require_percentage(recycled, 'recycledContentPercentage')
    require_repairability(repairability)
    if country and (len(country) != 2 or not country.isalpha()):
        raise ValidationAppError('Invalid country of origin.')

def get_product(db: Session, organization_id: uuid.UUID, product_id: uuid.UUID) -> Product:
    row = db.get(Product, product_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Product not found.')
    return row

def get_variant(db: Session, organization_id: uuid.UUID, variant_id: uuid.UUID) -> ProductVariant:
    row = db.get(ProductVariant, variant_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Product variant not found.')
    return row

def get_batch(db: Session, organization_id: uuid.UUID, batch_id: uuid.UUID) -> ProductBatch:
    row = db.get(ProductBatch, batch_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Product batch not found.')
    return row

def get_bom(db: Session, organization_id: uuid.UUID, bom_id: uuid.UUID) -> BillOfMaterials:
    row = db.get(BillOfMaterials, bom_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Bill of materials not found.')
    return row

def list_products(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, search: str | None=None, product_type: str | None=None, product_category: str | None=None, is_active: bool | None=None) -> Page[ProductResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(Product).where(Product.organization_id == organization_id)
    if search:
        like = f'%{search.strip()}%'
        stmt = stmt.where(or_(Product.name.ilike(like), Product.code.ilike(like), Product.sku.ilike(like)))
    if product_type:
        stmt = stmt.where(Product.product_type == product_type)
    if product_category:
        stmt = stmt.where(Product.product_category == product_category)
    if is_active is not None:
        stmt = stmt.where(Product.is_active.is_(is_active))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(Product.code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([ProductResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_product(db: Session, user: User, organization_id: uuid.UUID, payload: ProductCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ProductResponse:
    require_product_write(db, user, organization_id)
    code = payload.code.strip()
    country = payload.country_of_origin.upper() if payload.country_of_origin else None
    _validate_product_fields(db, product_type=payload.product_type, unit_code=payload.default_unit_code, weight=payload.weight_value, recyclability=payload.recyclability_percentage, recycled=payload.recycled_content_percentage, repairability=payload.repairability_score, country=country)
    if db.execute(select(Product.id).where(Product.organization_id == organization_id, Product.code == code)).scalar_one_or_none():
        raise ConflictError('Product code already exists in this organization.')
    row = Product(organization_id=organization_id, code=code, name=payload.name.strip(), description=payload.description, product_type=payload.product_type, product_category=payload.product_category, brand=payload.brand, model=payload.model, sku=payload.sku, gtin=payload.gtin, country_of_origin=country, default_unit_code=payload.default_unit_code, weight_value=payload.weight_value, weight_unit_code=payload.weight_unit_code, expected_lifetime_value=payload.expected_lifetime_value, expected_lifetime_unit=payload.expected_lifetime_unit, recyclability_percentage=payload.recyclability_percentage, recycled_content_percentage=payload.recycled_content_percentage, repairability_score=payload.repairability_score, is_active=payload.is_active, metadata_json=payload.metadata_json)
    db.add(row)
    db.flush()
    write_audit_log(db, action='product.created', actor_user_id=user.id, organization_id=organization_id, entity_type='product', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'code': row.code})
    db.commit()
    db.refresh(row)
    return ProductResponse.model_validate(row)

def update_product(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID, payload: ProductUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ProductResponse:
    require_product_write(db, user, organization_id)
    row = get_product(db, organization_id, product_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get('country_of_origin'):
        data['country_of_origin'] = data['country_of_origin'].upper()
    _validate_product_fields(db, product_type=data.get('product_type', row.product_type), unit_code=data.get('default_unit_code', row.default_unit_code), weight=data.get('weight_value', row.weight_value), recyclability=data.get('recyclability_percentage', row.recyclability_percentage), recycled=data.get('recycled_content_percentage', row.recycled_content_percentage), repairability=data.get('repairability_score', row.repairability_score), country=data.get('country_of_origin', row.country_of_origin))
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='product.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='product', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return ProductResponse.model_validate(row)

def archive_product(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> ProductResponse:
    require_product_manage(db, user, organization_id)
    row = get_product(db, organization_id, product_id)
    row.is_active = False
    write_audit_log(db, action='product.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='product', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return ProductResponse.model_validate(row)

def get_product_detail(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID) -> ProductResponse:
    ensure_org_access(db, user, organization_id)
    return ProductResponse.model_validate(get_product(db, organization_id, product_id))

def list_variants(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID) -> list[VariantResponse]:
    ensure_org_access(db, user, organization_id)
    get_product(db, organization_id, product_id)
    rows = list(db.execute(select(ProductVariant).where(ProductVariant.organization_id == organization_id, ProductVariant.product_id == product_id).order_by(ProductVariant.code.asc())).scalars().all())
    return [VariantResponse.model_validate(r) for r in rows]

def create_variant(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID, payload: VariantCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> VariantResponse:
    require_product_write(db, user, organization_id)
    product = get_product(db, organization_id, product_id)
    if not product.is_active:
        raise BusinessRuleError('Inactive products cannot receive new variants.')
    code = payload.code.strip()
    require_non_negative(payload.weight_value, 'weightValue')
    if db.execute(select(ProductVariant.id).where(ProductVariant.product_id == product_id, ProductVariant.code == code)).scalar_one_or_none():
        raise ConflictError('Variant code already exists for this product.')
    row = ProductVariant(organization_id=organization_id, product_id=product_id, code=code, name=payload.name.strip(), sku=payload.sku, gtin=payload.gtin, description=payload.description, attributes_json=payload.attributes_json, weight_value=payload.weight_value, weight_unit_code=payload.weight_unit_code, is_active=payload.is_active)
    db.add(row)
    db.flush()
    write_audit_log(db, action='product_variant.created', actor_user_id=user.id, organization_id=organization_id, entity_type='product_variant', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'productId': str(product_id), 'code': code})
    db.commit()
    db.refresh(row)
    return VariantResponse.model_validate(row)

def update_variant(db: Session, user: User, organization_id: uuid.UUID, variant_id: uuid.UUID, payload: VariantUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> VariantResponse:
    require_product_write(db, user, organization_id)
    row = get_variant(db, organization_id, variant_id)
    data = payload.model_dump(exclude_unset=True)
    if 'weight_value' in data:
        require_non_negative(data['weight_value'], 'weightValue')
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='product.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='product_variant', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return VariantResponse.model_validate(row)

def archive_variant(db: Session, user: User, organization_id: uuid.UUID, variant_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> VariantResponse:
    require_product_manage(db, user, organization_id)
    row = get_variant(db, organization_id, variant_id)
    row.is_active = False
    write_audit_log(db, action='product.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='product_variant', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return VariantResponse.model_validate(row)

def get_variant_detail(db: Session, user: User, organization_id: uuid.UUID, variant_id: uuid.UUID) -> VariantResponse:
    ensure_org_access(db, user, organization_id)
    return VariantResponse.model_validate(get_variant(db, organization_id, variant_id))

def _validate_batch_refs(db: Session, organization_id: uuid.UUID, *, product_id: uuid.UUID, variant_id: uuid.UUID | None, facility_id: uuid.UUID | None, production_line_id: uuid.UUID | None, production_date: date | None, expiration_date: date | None, quantity: Decimal, unit_code: str, status: str) -> None:
    get_product(db, organization_id, product_id)
    if variant_id:
        variant = get_variant(db, organization_id, variant_id)
        if variant.product_id != product_id:
            raise ValidationAppError('Variant does not belong to the product.')
    if facility_id:
        get_facility(db, organization_id, facility_id)
    if production_line_id:
        line = db.get(ProductionLine, production_line_id)
        if line is None or line.organization_id != organization_id:
            raise NotFoundError('Production line not found.')
        if facility_id and line.facility_id != facility_id:
            raise ValidationAppError('Production line must belong to the facility.')
    if production_date and expiration_date and (expiration_date < production_date):
        raise ValidationAppError('Expiration date cannot be earlier than production date.')
    require_positive(quantity, 'quantity')
    get_unit(db, unit_code)
    if status not in BATCH_STATUSES:
        raise ValidationAppError('Invalid batch status.')

def list_batches(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, product_id: uuid.UUID | None=None, status: str | None=None, search: str | None=None) -> Page[BatchResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(ProductBatch).where(ProductBatch.organization_id == organization_id)
    if product_id:
        stmt = stmt.where(ProductBatch.product_id == product_id)
    if status:
        stmt = stmt.where(ProductBatch.status == status)
    if search:
        stmt = stmt.where(ProductBatch.batch_code.ilike(f'%{search.strip()}%'))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(ProductBatch.batch_code.asc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([BatchResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def create_batch(db: Session, user: User, organization_id: uuid.UUID, payload: BatchCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BatchResponse:
    require_product_write(db, user, organization_id)
    code = payload.batch_code.strip()
    _validate_batch_refs(db, organization_id, product_id=payload.product_id, variant_id=payload.product_variant_id, facility_id=payload.facility_id, production_line_id=payload.production_line_id, production_date=payload.production_date, expiration_date=payload.expiration_date, quantity=payload.quantity, unit_code=payload.unit_code, status=payload.status)
    if db.execute(select(ProductBatch.id).where(ProductBatch.organization_id == organization_id, ProductBatch.batch_code == code)).scalar_one_or_none():
        raise ConflictError('Batch code already exists in this organization.')
    row = ProductBatch(organization_id=organization_id, product_id=payload.product_id, product_variant_id=payload.product_variant_id, facility_id=payload.facility_id, production_line_id=payload.production_line_id, batch_code=code, production_date=payload.production_date, expiration_date=payload.expiration_date, quantity=payload.quantity, unit_code=payload.unit_code, total_weight=payload.total_weight, weight_unit_code=payload.weight_unit_code, status=payload.status, traceability_reference=payload.traceability_reference, metadata_json=payload.metadata_json)
    db.add(row)
    db.flush()
    write_audit_log(db, action='product_batch.created', actor_user_id=user.id, organization_id=organization_id, entity_type='product_batch', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'batchCode': code})
    db.commit()
    db.refresh(row)
    return BatchResponse.model_validate(row)

def update_batch(db: Session, user: User, organization_id: uuid.UUID, batch_id: uuid.UUID, payload: BatchUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BatchResponse:
    require_product_write(db, user, organization_id)
    row = get_batch(db, organization_id, batch_id)
    if row.status in {'completed', 'released'}:
        raise BusinessRuleError('Completed and released batches are immutable except through controlled transitions.')
    data = payload.model_dump(exclude_unset=True)
    _validate_batch_refs(db, organization_id, product_id=row.product_id, variant_id=data.get('product_variant_id', row.product_variant_id), facility_id=data.get('facility_id', row.facility_id), production_line_id=data.get('production_line_id', row.production_line_id), production_date=data.get('production_date', row.production_date), expiration_date=data.get('expiration_date', row.expiration_date), quantity=data.get('quantity', row.quantity), unit_code=data.get('unit_code', row.unit_code), status=row.status)
    for key, value in data.items():
        setattr(row, key, value)
    write_audit_log(db, action='product.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='product_batch', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return BatchResponse.model_validate(row)

def transition_batch(db: Session, user: User, organization_id: uuid.UUID, batch_id: uuid.UUID, payload: BatchTransition, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BatchResponse:
    require_product_manage(db, user, organization_id)
    row = get_batch(db, organization_id, batch_id)
    allowed = BATCH_TRANSITIONS.get(row.status, frozenset())
    if payload.status not in allowed:
        raise BusinessRuleError(f"Cannot transition batch from '{row.status}' to '{payload.status}'.")
    previous = row.status
    row.status = payload.status
    write_audit_log(db, action='batch.status_changed', actor_user_id=user.id, organization_id=organization_id, entity_type='product_batch', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'from': previous, 'to': payload.status})
    db.commit()
    db.refresh(row)
    return BatchResponse.model_validate(row)

def get_batch_detail(db: Session, user: User, organization_id: uuid.UUID, batch_id: uuid.UUID) -> BatchResponse:
    ensure_org_access(db, user, organization_id)
    return BatchResponse.model_validate(get_batch(db, organization_id, batch_id))

def _component_cycle_exists(db: Session, organization_id: uuid.UUID, root_product_id: uuid.UUID, component_id: uuid.UUID) -> bool:
    if component_id == root_product_id:
        return True
    visited: set[uuid.UUID] = set()
    stack = [component_id]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        if current == root_product_id:
            return True
        bom_ids = list(db.execute(select(BillOfMaterials.id).where(BillOfMaterials.organization_id == organization_id, BillOfMaterials.product_id == current, BillOfMaterials.status.in_(['approved', 'draft', 'under_review']))).scalars().all())
        if not bom_ids:
            continue
        comps = list(db.execute(select(BillOfMaterialItem.component_product_id).where(BillOfMaterialItem.bill_of_material_id.in_(bom_ids), BillOfMaterialItem.component_product_id.is_not(None))).scalars().all())
        stack.extend((c for c in comps if c is not None))
    return False

def _validate_bom_item(db: Session, organization_id: uuid.UUID, product_id: uuid.UUID, item: BomItemCreate) -> None:
    has_mat = item.material_id is not None
    has_comp = item.component_product_id is not None
    if has_mat == has_comp:
        raise ValidationAppError('Each BOM item must reference either a material or a component product.')
    require_positive(item.quantity, 'quantity')
    get_unit(db, item.unit_code)
    require_percentage(item.waste_percentage, 'wastePercentage')
    require_percentage(item.recycled_content_percentage, 'recycledContentPercentage')
    require_percentage(item.allocation_percentage, 'allocationPercentage')
    if item.material_id:
        get_material(db, organization_id, item.material_id)
    if item.component_product_id:
        get_product(db, organization_id, item.component_product_id)
        if _component_cycle_exists(db, organization_id, product_id, item.component_product_id):
            raise BusinessRuleError('Circular component product relationship detected.')
    if item.supplier_id:
        get_supplier(db, organization_id, item.supplier_id)

def _bom_to_response(db: Session, bom: BillOfMaterials) -> BomResponse:
    items = list(db.execute(select(BillOfMaterialItem).where(BillOfMaterialItem.bill_of_material_id == bom.id).order_by(BillOfMaterialItem.created_at.asc())).scalars().all())
    base = BomResponse.model_validate(bom)
    base.items = [BomItemResponse.model_validate(i) for i in items]
    return base

def list_boms(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID) -> list[BomResponse]:
    ensure_org_access(db, user, organization_id)
    get_product(db, organization_id, product_id)
    rows = list(db.execute(select(BillOfMaterials).where(BillOfMaterials.organization_id == organization_id, BillOfMaterials.product_id == product_id).order_by(BillOfMaterials.version.desc())).scalars().all())
    return [_bom_to_response(db, r) for r in rows]

def create_bom(db: Session, user: User, organization_id: uuid.UUID, product_id: uuid.UUID, payload: BomCreate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BomResponse:
    require_product_write(db, user, organization_id)
    get_product(db, organization_id, product_id)
    if payload.product_variant_id:
        variant = get_variant(db, organization_id, payload.product_variant_id)
        if variant.product_id != product_id:
            raise ValidationAppError('Variant does not belong to the product.')
    if payload.valid_from and payload.valid_to and (payload.valid_to < payload.valid_from):
        raise ValidationAppError('validTo cannot be earlier than validFrom.')
    for item in payload.items:
        _validate_bom_item(db, organization_id, product_id, item)
    version = db.execute(select(func.coalesce(func.max(BillOfMaterials.version), 0)).where(BillOfMaterials.product_id == product_id)).scalar_one() + 1
    bom = BillOfMaterials(organization_id=organization_id, product_id=product_id, product_variant_id=payload.product_variant_id, version=version, name=payload.name.strip(), description=payload.description, status='draft', valid_from=payload.valid_from, valid_to=payload.valid_to)
    db.add(bom)
    db.flush()
    for item in payload.items:
        db.add(BillOfMaterialItem(bill_of_material_id=bom.id, material_id=item.material_id, component_product_id=item.component_product_id, supplier_id=item.supplier_id, quantity=item.quantity, unit_code=item.unit_code, waste_percentage=item.waste_percentage, recycled_content_percentage=item.recycled_content_percentage, source_country_code=item.source_country_code.upper() if item.source_country_code else None, transport_distance_km=item.transport_distance_km, transport_mode=item.transport_mode, allocation_percentage=item.allocation_percentage, notes=item.notes, metadata_json=item.metadata_json))
    write_audit_log(db, action='bom.created', actor_user_id=user.id, organization_id=organization_id, entity_type='bill_of_materials', entity_id=str(bom.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'version': version})
    db.commit()
    db.refresh(bom)
    return _bom_to_response(db, bom)

def update_bom(db: Session, user: User, organization_id: uuid.UUID, bom_id: uuid.UUID, payload: BomUpdate, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BomResponse:
    require_product_write(db, user, organization_id)
    bom = get_bom(db, organization_id, bom_id)
    if bom.status not in {'draft', 'under_review'}:
        raise BusinessRuleError('Approved BOM versions are immutable. Clone a new version.')
    data = payload.model_dump(exclude_unset=True)
    items = data.pop('items', None)
    valid_from = data.get('valid_from', bom.valid_from)
    valid_to = data.get('valid_to', bom.valid_to)
    if valid_from and valid_to and (valid_to < valid_from):
        raise ValidationAppError('validTo cannot be earlier than validFrom.')
    for key, value in data.items():
        setattr(bom, key, value)
    if items is not None:
        for item in items:
            _validate_bom_item(db, organization_id, bom.product_id, BomItemCreate.model_validate(item))
        existing = list(db.execute(select(BillOfMaterialItem).where(BillOfMaterialItem.bill_of_material_id == bom.id)).scalars().all())
        for e in existing:
            db.delete(e)
        db.flush()
        for item in items:
            model = BomItemCreate.model_validate(item)
            db.add(BillOfMaterialItem(bill_of_material_id=bom.id, material_id=model.material_id, component_product_id=model.component_product_id, supplier_id=model.supplier_id, quantity=model.quantity, unit_code=model.unit_code, waste_percentage=model.waste_percentage, recycled_content_percentage=model.recycled_content_percentage, source_country_code=model.source_country_code.upper() if model.source_country_code else None, transport_distance_km=model.transport_distance_km, transport_mode=model.transport_mode, allocation_percentage=model.allocation_percentage, notes=model.notes, metadata_json=model.metadata_json))
    write_audit_log(db, action='product.updated', actor_user_id=user.id, organization_id=organization_id, entity_type='bill_of_materials', entity_id=str(bom.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(bom)
    return _bom_to_response(db, bom)

def submit_bom_review(db: Session, user: User, organization_id: uuid.UUID, bom_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BomResponse:
    require_product_write(db, user, organization_id)
    bom = get_bom(db, organization_id, bom_id)
    if bom.status != 'draft':
        raise BusinessRuleError('Only draft BOMs can be submitted for review.')
    bom.status = 'under_review'
    write_audit_log(db, action='bom.submitted', actor_user_id=user.id, organization_id=organization_id, entity_type='bill_of_materials', entity_id=str(bom.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(bom)
    return _bom_to_response(db, bom)

def approve_bom(db: Session, user: User, organization_id: uuid.UUID, bom_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BomResponse:
    require_product_approve(db, user, organization_id)
    bom = get_bom(db, organization_id, bom_id)
    if bom.status not in {'draft', 'under_review'}:
        raise BusinessRuleError('BOM cannot be approved from current status.')
    if bom.valid_from:
        overlapping = list(db.execute(select(BillOfMaterials).where(BillOfMaterials.product_id == bom.product_id, BillOfMaterials.id != bom.id, BillOfMaterials.status == 'approved')).scalars().all())
        for other in overlapping:
            if not other.valid_from:
                continue
            a0, a1 = (bom.valid_from, bom.valid_to)
            b0, b1 = (other.valid_from, other.valid_to)
            if a1 is None:
                a1 = date.max
            if b1 is None:
                b1 = date.max
            if a0 <= b1 and b0 <= a1:
                raise BusinessRuleError('Only one active approved BOM version may apply at a given date.')
    for other in db.execute(select(BillOfMaterials).where(BillOfMaterials.product_id == bom.product_id, BillOfMaterials.id != bom.id, BillOfMaterials.status == 'approved')).scalars().all():
        if bom.valid_from is None and other.valid_from is None:
            other.status = 'superseded'
    bom.status = 'approved'
    bom.approved_by_user_id = user.id
    bom.approved_at = datetime.now(UTC)
    write_audit_log(db, action='bom.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='bill_of_materials', entity_id=str(bom.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(bom)
    return _bom_to_response(db, bom)

def clone_bom_version(db: Session, user: User, organization_id: uuid.UUID, bom_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BomResponse:
    require_product_write(db, user, organization_id)
    source = get_bom(db, organization_id, bom_id)
    items = list(db.execute(select(BillOfMaterialItem).where(BillOfMaterialItem.bill_of_material_id == source.id)).scalars().all())
    payload = BomCreate(product_variant_id=source.product_variant_id, name=f'{source.name} (v next)', description=source.description, valid_from=source.valid_from, valid_to=source.valid_to, items=[BomItemCreate(material_id=i.material_id, component_product_id=i.component_product_id, supplier_id=i.supplier_id, quantity=i.quantity, unit_code=i.unit_code, waste_percentage=i.waste_percentage, recycled_content_percentage=i.recycled_content_percentage, source_country_code=i.source_country_code, transport_distance_km=i.transport_distance_km, transport_mode=i.transport_mode, allocation_percentage=i.allocation_percentage, notes=i.notes, metadata_json=i.metadata_json) for i in items])
    result = create_bom(db, user, organization_id, source.product_id, payload, request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    write_audit_log(db, action='bom.version_cloned', actor_user_id=user.id, organization_id=organization_id, entity_type='bill_of_materials', entity_id=str(result.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'sourceBomId': str(source.id)})
    db.commit()
    return result

def archive_bom(db: Session, user: User, organization_id: uuid.UUID, bom_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> BomResponse:
    require_product_manage(db, user, organization_id)
    bom = get_bom(db, organization_id, bom_id)
    if bom.status not in BOM_STATUSES:
        raise ValidationAppError('Invalid BOM status.')
    bom.status = 'archived'
    write_audit_log(db, action='product.archived', actor_user_id=user.id, organization_id=organization_id, entity_type='bill_of_materials', entity_id=str(bom.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(bom)
    return _bom_to_response(db, bom)

def get_bom_detail(db: Session, user: User, organization_id: uuid.UUID, bom_id: uuid.UUID) -> BomResponse:
    ensure_org_access(db, user, organization_id)
    return _bom_to_response(db, get_bom(db, organization_id, bom_id))
