from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import RECORD_SOURCE_TYPES, require_unit
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    get_installation_for_org,
    get_product_profile_for_org,
    require_positive_quantity,
    require_usable_installation,
    require_writable_binding,
    validate_optional_date_range,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import CbamProductionRecord
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class ProductionRecordCreate(CamelModel):
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None = None
    production_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    quantity: Decimal
    unit: str
    notes: str | None = None
    source_type: str = 'MANUAL'


class ProductionRecordUpdate(CamelModel):
    row_version: int
    product_profile_version_id: uuid.UUID | None = None
    production_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    notes: str | None = None


class ProductionRecordVersionRequest(CamelModel):
    row_version: int


class ProductionRecordResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None
    production_date: date | None
    period_start: date | None
    period_end: date | None
    quantity: Decimal
    unit: str
    notes: str | None
    source_type: str
    status: str
    row_version: int


def _to_response(row: CbamProductionRecord) -> ProductionRecordResponse:
    return ProductionRecordResponse.model_validate(row)


def _get_row(
    db: Session, organization_id: uuid.UUID, record_id: uuid.UUID
) -> CbamProductionRecord:
    row = db.get(CbamProductionRecord, record_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM production record not found.')
    return row


def list_production_records(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    include_archived: bool = False,
) -> Page[ProductionRecordResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamProductionRecord).where(
        CbamProductionRecord.organization_id == organization_id,
        CbamProductionRecord.reporting_period_binding_id == binding_id,
    )
    if not include_archived:
        stmt = stmt.where(CbamProductionRecord.status == 'active')
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamProductionRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_production_record(
    db: Session, user: User, organization_id: uuid.UUID, record_id: uuid.UUID
) -> ProductionRecordResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_row(db, organization_id, record_id))


def create_production_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: ProductionRecordCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionRecordResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    installation = get_installation_for_org(db, organization_id, payload.installation_profile_id)
    require_usable_installation(installation)
    product_profile_id = payload.product_profile_version_id
    if product_profile_id is not None:
        get_product_profile_for_org(db, organization_id, product_profile_id)
    require_positive_quantity(payload.quantity)
    unit = require_unit(payload.unit)
    if payload.source_type not in RECORD_SOURCE_TYPES:
        raise ValidationAppError('Invalid sourceType.')
    validate_optional_date_range(payload.period_start, payload.period_end)
    row = CbamProductionRecord(
        organization_id=organization_id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        product_profile_version_id=product_profile_id,
        production_date=payload.production_date,
        period_start=payload.period_start,
        period_end=payload.period_end,
        quantity=payload.quantity,
        unit=unit,
        notes=payload.notes,
        source_type=payload.source_type,
        status='active',
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action='cbam.production_record.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_production_record',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'bindingId': str(binding.id),
            'installationProfileId': str(installation.id),
            'quantity': str(row.quantity),
            'unit': row.unit,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_production_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ProductionRecordUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionRecordResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    if row.status == 'archived':
        raise BusinessRuleError('Archived production records cannot be updated.')
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM production record')
    data = payload.model_dump(exclude_unset=True, exclude={'row_version'})
    if 'product_profile_version_id' in data:
        pid = data['product_profile_version_id']
        if pid is not None:
            get_product_profile_for_org(db, organization_id, pid)
        row.product_profile_version_id = pid
    if 'quantity' in data and data['quantity'] is not None:
        require_positive_quantity(data['quantity'])
        row.quantity = data['quantity']
    if 'unit' in data and data['unit'] is not None:
        row.unit = require_unit(data['unit'])
    for field in ('production_date', 'period_start', 'period_end', 'notes'):
        if field in data:
            setattr(row, field, data[field])
    validate_optional_date_range(row.period_start, row.period_end)
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.production_record.updated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_production_record',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'fields': list(data.keys()), 'rowVersion': row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_production_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ProductionRecordVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionRecordResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM production record')
    if row.status == 'archived':
        raise BusinessRuleError('Production record is already archived.')
    row.status = 'archived'
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.production_record.archived',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_production_record',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'to': 'archived'},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)
