"""CBAM production records with authoritative product-profile linkage (Phase 6C)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import RECORD_SOURCE_TYPES, require_unit
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    get_installation_for_org,
    require_positive_quantity,
    require_usable_installation,
    require_writable_binding,
    validate_optional_date_range,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.application.production_profile_link import (
    compute_profile_link_state,
    require_linkable_product_profile,
    require_production_profile_id,
)
from ecotrace.modules.cbam.infrastructure.models import CbamProductionRecord
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

ProfileLinkStatus = Literal['MISSING', 'READY', 'OUTDATED', 'INVALID']


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
    # Phase 6C authoritative profile-link projection (from referenced immutable version).
    product_id: uuid.UUID | None = None
    product_name: str | None = None
    profile_version: int | None = None
    profile_status: str | None = None
    cn_normalized_code: str | None = None
    cn_display_code: str | None = None
    classification_ready: bool | None = None
    profile_link_status: ProfileLinkStatus
    profile_link_issue_codes: list[str]


class ProductionProfileLinkSummary(CamelModel):
    eligible_record_count: int
    missing_profile_count: int
    outdated_profile_count: int
    invalid_profile_count: int
    active_record_count: int
    allocation_profile_ready: bool
    blocking_issue_codes: list[str]


def _to_response(db: Session, row: CbamProductionRecord) -> ProductionRecordResponse:
    status, codes, profile = compute_profile_link_state(db, row)
    return ProductionRecordResponse(
        id=row.id,
        organization_id=row.organization_id,
        reporting_period_binding_id=row.reporting_period_binding_id,
        installation_profile_id=row.installation_profile_id,
        product_profile_version_id=row.product_profile_version_id,
        production_date=row.production_date,
        period_start=row.period_start,
        period_end=row.period_end,
        quantity=row.quantity,
        unit=row.unit,
        notes=row.notes,
        source_type=row.source_type,
        status=row.status,
        row_version=row.row_version,
        product_id=profile.product_id if profile else None,
        product_name=profile.product_name if profile else None,
        profile_version=profile.version if profile else None,
        profile_status=profile.status if profile else None,
        cn_normalized_code=profile.cn_normalized_code if profile else None,
        cn_display_code=profile.cn_display_code if profile else None,
        classification_ready=profile.classification_ready if profile else None,
        profile_link_status=status,
        profile_link_issue_codes=codes,
    )


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
        [_to_response(db, r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def get_production_record(
    db: Session, user: User, organization_id: uuid.UUID, record_id: uuid.UUID
) -> ProductionRecordResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(db, _get_row(db, organization_id, record_id))


def get_production_profile_link_summary(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
) -> ProductionProfileLinkSummary:
    """Binding-scoped authoritative counts (not derived from one paginated page)."""
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    rows = list(
        db.execute(
            select(CbamProductionRecord).where(
                CbamProductionRecord.organization_id == organization_id,
                CbamProductionRecord.reporting_period_binding_id == binding_id,
                CbamProductionRecord.status == 'active',
            )
        )
        .scalars()
        .all()
    )
    eligible = 0
    missing = 0
    outdated = 0
    invalid = 0
    for row in rows:
        status, _, _ = compute_profile_link_state(db, row)
        if status == 'MISSING':
            missing += 1
        elif status == 'OUTDATED':
            outdated += 1
            eligible += 1
        elif status == 'READY':
            eligible += 1
        else:
            invalid += 1
    blocking: list[str] = []
    if missing:
        blocking.append('PRODUCTION_PROFILE_LINK_MISSING')
    if invalid:
        blocking.append('PRODUCTION_PROFILE_LINK_INVALID')
    if not rows:
        blocking.append('PRODUCTION_RECORDS_REQUIRED')
    allocation_ready = missing == 0 and invalid == 0 and eligible > 0
    return ProductionProfileLinkSummary(
        eligible_record_count=eligible,
        missing_profile_count=missing,
        outdated_profile_count=outdated,
        invalid_profile_count=invalid,
        active_record_count=len(rows),
        allocation_profile_ready=allocation_ready,
        blocking_issue_codes=blocking,
    )


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
    profile_id = require_production_profile_id(payload.product_profile_version_id)
    profile = require_linkable_product_profile(db, organization_id, profile_id)
    require_positive_quantity(payload.quantity)
    unit = require_unit(payload.unit)
    if payload.source_type not in RECORD_SOURCE_TYPES:
        raise ValidationAppError('Invalid sourceType.')
    validate_optional_date_range(payload.period_start, payload.period_end)
    row = CbamProductionRecord(
        organization_id=organization_id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        product_profile_version_id=profile.id,
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
            'productProfileVersionId': str(profile.id),
            'productId': str(profile.product_id),
            'quantity': str(row.quantity),
            'unit': row.unit,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


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
        if pid is None:
            raise BusinessRuleError(
                'Select a published product profile before saving production data.',
                details=[{'code': 'PRODUCT_PROFILE_REQUIRED'}],
            )
        profile = require_linkable_product_profile(db, organization_id, pid)
        row.product_profile_version_id = profile.id
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
    return _to_response(db, row)


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
    from ecotrace.modules.cbam.application.direct_emissions_allocation_service import (
        assert_production_record_not_referenced,
    )

    assert_production_record_not_referenced(
        db, organization_id=organization_id, production_record_id=row.id
    )
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
    return _to_response(db, row)


# Re-export for typed callers / tests.
__all__ = [
    'ProductionProfileLinkSummary',
    'ProductionRecordCreate',
    'ProductionRecordResponse',
    'ProductionRecordUpdate',
    'ProductionRecordVersionRequest',
    'archive_production_record',
    'create_production_record',
    'get_production_profile_link_summary',
    'get_production_record',
    'list_production_records',
    'update_production_record',
]
