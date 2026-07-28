from __future__ import annotations
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, NotFoundError
from ecotrace.core.lca_constants import DISCLAIMER
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.product_carbon_footprint.infrastructure.models import ProductCarbonFootprint
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_product_approve
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

class FootprintResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    lca_study_id: uuid.UUID
    calculation_run_id: uuid.UUID
    product_id: uuid.UUID
    product_variant_id: uuid.UUID | None
    product_batch_id: uuid.UUID | None
    functional_unit_quantity: Decimal
    functional_unit_code: str
    total_kg_co2e: Decimal
    cradle_to_gate_kg_co2e: Decimal | None
    use_phase_kg_co2e: Decimal | None
    end_of_life_kg_co2e: Decimal | None
    biogenic_co2_kg: Decimal | None
    status: str
    approved_by_user_id: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
    disclaimer: str = DISCLAIMER

def get_footprint(db: Session, organization_id: uuid.UUID, footprint_id: uuid.UUID) -> ProductCarbonFootprint:
    row = db.get(ProductCarbonFootprint, footprint_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('Product carbon footprint not found.')
    return row

def list_footprints(db: Session, user: User, organization_id: uuid.UUID, *, page: int, page_size: int, product_id: uuid.UUID | None=None, status: str | None=None) -> Page[FootprintResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(ProductCarbonFootprint).where(ProductCarbonFootprint.organization_id == organization_id)
    if product_id:
        stmt = stmt.where(ProductCarbonFootprint.product_id == product_id)
    if status:
        stmt = stmt.where(ProductCarbonFootprint.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(db.execute(stmt.order_by(ProductCarbonFootprint.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all())
    return paginate([FootprintResponse.model_validate(r) for r in rows], page=page, page_size=page_size, total_items=int(total))

def get_footprint_detail(db: Session, user: User, organization_id: uuid.UUID, footprint_id: uuid.UUID) -> FootprintResponse:
    ensure_org_access(db, user, organization_id)
    return FootprintResponse.model_validate(get_footprint(db, organization_id, footprint_id))

def approve_footprint(db: Session, user: User, organization_id: uuid.UUID, footprint_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FootprintResponse:
    require_product_approve(db, user, organization_id)
    row = get_footprint(db, organization_id, footprint_id)
    if row.status == 'approved':
        raise BusinessRuleError('Footprint is already approved.')
    if row.status not in {'calculated', 'under_review', 'draft'}:
        raise BusinessRuleError('Footprint cannot be approved from current status.')
    others = list(db.execute(select(ProductCarbonFootprint).where(ProductCarbonFootprint.organization_id == organization_id, ProductCarbonFootprint.product_id == row.product_id, ProductCarbonFootprint.product_variant_id == row.product_variant_id, ProductCarbonFootprint.product_batch_id == row.product_batch_id, ProductCarbonFootprint.lca_study_id == row.lca_study_id, ProductCarbonFootprint.id != row.id, ProductCarbonFootprint.status == 'approved')).scalars().all())
    for other in others:
        other.status = 'superseded'
    row.status = 'approved'
    row.approved_by_user_id = user.id
    row.approved_at = datetime.now(UTC)
    write_audit_log(db, action='product_carbon_footprint.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='product_carbon_footprint', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent)
    db.commit()
    db.refresh(row)
    return FootprintResponse.model_validate(row)

def supersede_footprint(db: Session, user: User, organization_id: uuid.UUID, footprint_id: uuid.UUID, *, request_id: str | None=None, ip_address: str | None=None, user_agent: str | None=None) -> FootprintResponse:
    require_product_approve(db, user, organization_id)
    row = get_footprint(db, organization_id, footprint_id)
    if row.status != 'approved':
        raise BusinessRuleError('Only approved footprints can be superseded.')
    row.status = 'superseded'
    write_audit_log(db, action='product_carbon_footprint.approved', actor_user_id=user.id, organization_id=organization_id, entity_type='product_carbon_footprint', entity_id=str(row.id), request_id=request_id, ip_address=ip_address, user_agent=user_agent, metadata={'status': 'superseded'})
    db.commit()
    db.refresh(row)
    return FootprintResponse.model_validate(row)
