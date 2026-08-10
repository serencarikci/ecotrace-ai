from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import is_known_factor_unit
from ecotrace.modules.cbam.application.collection_guards import require_positive_quantity
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.factor_catalog_seed import ensure_platform_factor_catalog
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamFactorDefinition,
    CbamFactorValue,
    CbamReferenceSource,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class FactorDefinitionResponse(CamelModel):
    id: uuid.UUID
    code: str
    name: str
    factor_category: str
    activity_type: str | None
    property_code: str | None
    input_unit_family: str | None
    output_unit: str | None
    description: str | None
    status: str


class FactorValueCreate(CamelModel):
    reference_source_id: uuid.UUID
    activity_type: str | None = None
    numeric_value: Decimal
    unit: str
    valid_from: date | None = None
    valid_until: date | None = None
    geography_code: str | None = None
    supplier_name: str | None = None
    facility_specific: bool = False
    data_source_type: str
    source_reference: str | None = None
    notes: str | None = None
    organization_scoped: bool = True


class FactorValueUpdate(CamelModel):
    row_version: int
    numeric_value: Decimal | None = None
    unit: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    geography_code: str | None = None
    supplier_name: str | None = None
    facility_specific: bool | None = None
    source_reference: str | None = None
    notes: str | None = None
    activity_type: str | None = None


class FactorValueVersionRequest(CamelModel):
    row_version: int


class FactorValueResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    factor_definition_id: uuid.UUID
    reference_source_id: uuid.UUID
    activity_type: str | None
    numeric_value: Decimal
    unit: str
    valid_from: date | None
    valid_until: date | None
    geography_code: str | None
    supplier_name: str | None
    facility_specific: bool
    data_source_type: str
    source_reference: str | None
    notes: str | None
    status: str
    row_version: int
    archived_at: datetime | None


def _def_response(row: CbamFactorDefinition) -> FactorDefinitionResponse:
    return FactorDefinitionResponse.model_validate(row)


def _val_response(row: CbamFactorValue) -> FactorValueResponse:
    return FactorValueResponse.model_validate(row)


def get_definition_by_code(db: Session, code: str) -> CbamFactorDefinition:
    ensure_platform_factor_catalog(db)
    row = db.execute(
        select(CbamFactorDefinition).where(CbamFactorDefinition.code == code.strip())
    ).scalar_one_or_none()
    if row is None or row.status != 'ACTIVE':
        raise NotFoundError('CBAM factor definition not found.')
    return row


def list_factor_definitions(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[FactorDefinitionResponse]:
    require_cbam_view(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    stmt = select(CbamFactorDefinition).where(CbamFactorDefinition.status == 'ACTIVE')
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamFactorDefinition.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_def_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_factor_definition(
    db: Session, user: User, organization_id: uuid.UUID, definition_id: uuid.UUID
) -> FactorDefinitionResponse:
    require_cbam_view(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    row = db.get(CbamFactorDefinition, definition_id)
    if row is None:
        raise NotFoundError('CBAM factor definition not found.')
    return _def_response(row)


def _get_org_value(
    db: Session, organization_id: uuid.UUID, value_id: uuid.UUID
) -> CbamFactorValue:
    row = db.get(CbamFactorValue, value_id)
    if row is None:
        raise NotFoundError('CBAM factor value not found.')
    if row.organization_id is not None and row.organization_id != organization_id:
        raise NotFoundError('CBAM factor value not found.')
    return row


def list_factor_values(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    definition_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    include_archived: bool = False,
) -> Page[FactorValueResponse]:
    require_cbam_view(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    definition = db.get(CbamFactorDefinition, definition_id)
    if definition is None:
        raise NotFoundError('CBAM factor definition not found.')
    stmt = select(CbamFactorValue).where(
        CbamFactorValue.factor_definition_id == definition_id,
        or_(
            CbamFactorValue.organization_id.is_(None),
            CbamFactorValue.organization_id == organization_id,
        ),
    )
    if not include_archived:
        stmt = stmt.where(CbamFactorValue.status != 'ARCHIVED')
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamFactorValue.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_val_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_factor_value(
    db: Session, user: User, organization_id: uuid.UUID, value_id: uuid.UUID
) -> FactorValueResponse:
    require_cbam_view(db, user, organization_id)
    return _val_response(_get_org_value(db, organization_id, value_id))


def create_factor_value(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    definition_id: uuid.UUID,
    payload: FactorValueCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorValueResponse:
    require_cbam_configure(db, user, organization_id)
    ensure_platform_factor_catalog(db)
    definition = db.get(CbamFactorDefinition, definition_id)
    if definition is None or definition.status != 'ACTIVE':
        raise NotFoundError('CBAM factor definition not found.')
    source = db.get(CbamReferenceSource, payload.reference_source_id)
    if source is None or source.status != 'ACTIVE':
        raise NotFoundError('CBAM reference source not found.')
    if source.organization_id is not None and source.organization_id != organization_id:
        raise NotFoundError('CBAM reference source not found.')
    if payload.data_source_type not in {'PRIMARY', 'DEFAULT_REFERENCE'}:
        raise ValidationAppError('Invalid dataSourceType.')
    require_positive_quantity(payload.numeric_value, field='numericValue')
    unit = payload.unit.strip()
    if not is_known_factor_unit(unit):
        raise ValidationAppError(f'Unsupported factor unit: {unit}')
    if payload.valid_from and payload.valid_until and payload.valid_until < payload.valid_from:
        raise ValidationAppError('validUntil must be on or after validFrom.')
    org_id = organization_id if payload.organization_scoped else None
    if payload.data_source_type == 'PRIMARY' and org_id is None:
        raise ValidationAppError('PRIMARY factor values must be organization-scoped.')
    row = CbamFactorValue(
        organization_id=org_id,
        factor_definition_id=definition.id,
        reference_source_id=source.id,
        activity_type=payload.activity_type,
        numeric_value=payload.numeric_value,
        unit=unit,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        geography_code=payload.geography_code,
        supplier_name=payload.supplier_name,
        facility_specific=payload.facility_specific,
        data_source_type=payload.data_source_type,
        source_reference=payload.source_reference,
        notes=payload.notes,
        status='DRAFT',
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action='cbam.factor_value.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_factor_value',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'factorDefinitionId': str(definition.id),
            'dataSourceType': row.data_source_type,
            'numericValue': str(row.numeric_value),
            'unit': row.unit,
        },
    )
    db.commit()
    db.refresh(row)
    return _val_response(row)


def update_factor_value(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    value_id: uuid.UUID,
    payload: FactorValueUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorValueResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_org_value(db, organization_id, value_id)
    if row.organization_id != organization_id:
        raise BusinessRuleError('Only organization-scoped factor values can be updated.')
    if row.status != 'DRAFT':
        raise BusinessRuleError('Only DRAFT factor values can be updated.')
    check_row_version(row.row_version, payload.row_version, entity='CBAM factor value')
    data = payload.model_dump(exclude_unset=True, exclude={'row_version'})
    if 'numeric_value' in data and data['numeric_value'] is not None:
        require_positive_quantity(data['numeric_value'], field='numericValue')
        row.numeric_value = data['numeric_value']
    if 'unit' in data and data['unit'] is not None:
        unit = data['unit'].strip()
        if not is_known_factor_unit(unit):
            raise ValidationAppError(f'Unsupported factor unit: {unit}')
        row.unit = unit
    for field in (
        'valid_from',
        'valid_until',
        'geography_code',
        'supplier_name',
        'facility_specific',
        'source_reference',
        'notes',
        'activity_type',
    ):
        if field in data:
            setattr(row, field, data[field])
    if row.valid_from and row.valid_until and row.valid_until < row.valid_from:
        raise ValidationAppError('validUntil must be on or after validFrom.')
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.factor_value.updated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_factor_value',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'fields': list(data.keys()), 'rowVersion': row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _val_response(row)


def activate_factor_value(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    value_id: uuid.UUID,
    payload: FactorValueVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorValueResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_org_value(db, organization_id, value_id)
    if row.organization_id != organization_id:
        raise BusinessRuleError('Only organization-scoped factor values can be activated.')
    check_row_version(row.row_version, payload.row_version, entity='CBAM factor value')
    if row.status == 'ARCHIVED':
        raise BusinessRuleError('Archived factor values cannot be activated.')
    if row.status == 'ACTIVE':
        raise BusinessRuleError('Factor value is already ACTIVE.')
    source = db.get(CbamReferenceSource, row.reference_source_id)
    if source is None or source.status != 'ACTIVE':
        raise BusinessRuleError('ACTIVE factor values require an ACTIVE reference source.')
    row.status = 'ACTIVE'
    row.reviewed_by_user_id = user.id
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.factor_value.activated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_factor_value',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'dataSourceType': row.data_source_type,
            'numericValue': str(row.numeric_value),
            'unit': row.unit,
        },
    )
    db.commit()
    db.refresh(row)
    return _val_response(row)


def archive_factor_value(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    value_id: uuid.UUID,
    payload: FactorValueVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> FactorValueResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_org_value(db, organization_id, value_id)
    if row.organization_id != organization_id:
        raise BusinessRuleError('Only organization-scoped factor values can be archived.')
    check_row_version(row.row_version, payload.row_version, entity='CBAM factor value')
    if row.status == 'ARCHIVED':
        raise BusinessRuleError('Factor value is already archived.')
    row.status = 'ARCHIVED'
    row.archived_at = datetime.now(UTC)
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.factor_value.archived',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_factor_value',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'to': 'ARCHIVED'},
    )
    db.commit()
    db.refresh(row)
    return _val_response(row)
