from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import (
    ACTIVITY_PROPERTY_CODES,
    BIOGENIC_STATUSES,
    DATA_SOURCE_TYPES,
    PROCESS_TYPE_CODES,
    get_activity_type,
    get_property_unit,
    require_unit,
    unit_compatible,
)
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
from ecotrace.modules.cbam.infrastructure.models import CbamActivityProperty, CbamActivityRecord
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class ActivityPropertyInput(CamelModel):
    property_code: str
    numeric_value: Decimal
    unit: str
    source_type: str = 'PRIMARY'
    source_reference: str | None = None


class ActivityRecordCreate(CamelModel):
    installation_profile_id: uuid.UUID
    activity_type: str
    activity_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    quantity: Decimal
    unit: str
    data_source_type: str
    source_reference: str | None = None
    measurement_method: str | None = None
    supplier_name: str | None = None
    certificate_reference: str | None = None
    process_type_code: str | None = None
    process_description: str | None = None
    biogenic_status: str | None = None
    notes: str | None = None
    properties: list[ActivityPropertyInput] | None = None


class ActivityRecordUpdate(CamelModel):
    row_version: int
    activity_date: date | None = None
    period_start: date | None = None
    period_end: date | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    data_source_type: str | None = None
    source_reference: str | None = None
    measurement_method: str | None = None
    supplier_name: str | None = None
    certificate_reference: str | None = None
    process_type_code: str | None = None
    process_description: str | None = None
    biogenic_status: str | None = None
    notes: str | None = None


class ActivityRecordVersionRequest(CamelModel):
    row_version: int


class ActivityPropertyResponse(CamelModel):
    id: uuid.UUID
    property_code: str
    numeric_value: Decimal
    unit: str
    source_type: str
    source_reference: str | None


class ActivityRecordResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    installation_profile_id: uuid.UUID
    activity_group: str
    activity_type: str
    activity_date: date | None
    period_start: date | None
    period_end: date | None
    quantity: Decimal
    unit: str
    data_source_type: str
    source_reference: str | None
    measurement_method: str | None
    supplier_name: str | None
    certificate_reference: str | None
    process_type_code: str | None
    process_description: str | None
    biogenic_status: str | None
    notes: str | None
    status: str
    row_version: int
    properties: list[ActivityPropertyResponse] = Field(default_factory=list)


def _load_properties(
    db: Session, record_id: uuid.UUID
) -> list[ActivityPropertyResponse]:
    rows = (
        db.execute(
            select(CbamActivityProperty).where(
                CbamActivityProperty.activity_record_id == record_id
            )
        )
        .scalars()
        .all()
    )
    return [
        ActivityPropertyResponse(
            id=p.id,
            property_code=p.property_code,
            numeric_value=p.numeric_value,
            unit=p.unit,
            source_type=p.source_type,
            source_reference=p.source_reference,
        )
        for p in rows
    ]


def _to_response(db: Session, row: CbamActivityRecord) -> ActivityRecordResponse:
    base = ActivityRecordResponse.model_validate(row)
    base.properties = _load_properties(db, row.id)
    return base


def _get_row(
    db: Session, organization_id: uuid.UUID, record_id: uuid.UUID
) -> CbamActivityRecord:
    row = db.get(CbamActivityRecord, record_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError('CBAM activity record not found.')
    return row


def _validate_activity_and_unit(activity_type: str, unit: str) -> tuple[str, str, str]:
    type_def = get_activity_type(activity_type.strip())
    if type_def is None:
        raise ValidationAppError(f'Unsupported activityType: {activity_type}')
    unit_code = require_unit(unit)
    if not unit_compatible(unit_code, type_def.allowed_unit_family):
        raise ValidationAppError(
            f'Unit {unit_code} is not compatible with activity type {type_def.code} '
            f'(expected family {type_def.allowed_unit_family}).'
        )
    return type_def.code, type_def.activity_group, unit_code


def _validate_process_fields(
    activity_group: str,
    process_type_code: str | None,
    process_description: str | None,
    biogenic_status: str | None,
) -> None:
    if biogenic_status is not None and biogenic_status not in BIOGENIC_STATUSES:
        raise ValidationAppError('Invalid biogenicStatus.')
    if activity_group != 'PROCESS':
        return
    if not process_type_code:
        raise ValidationAppError('processTypeCode is required for PROCESS activities.')
    if process_type_code not in PROCESS_TYPE_CODES:
        raise ValidationAppError(
            'Unsupported processTypeCode. Use OTHER_PROCESS with a description '
            '(sector-specific codes are BLOCKED until B-12).'
        )
    if process_type_code == 'OTHER_PROCESS' and not (process_description or '').strip():
        raise ValidationAppError('processDescription is required for OTHER_PROCESS.')


def _add_properties(
    db: Session,
    *,
    organization_id: uuid.UUID,
    activity_id: uuid.UUID,
    user_id: uuid.UUID,
    properties: list[ActivityPropertyInput] | None,
    data_source_type: str,
) -> None:
    if not properties:
        return
    if data_source_type != 'PRIMARY':
        raise ValidationAppError(
            'Activity properties may only be supplied when dataSourceType is PRIMARY.'
        )
    seen: set[str] = set()
    for prop in properties:
        code = prop.property_code.strip()
        if code not in ACTIVITY_PROPERTY_CODES:
            raise ValidationAppError(f'Unsupported propertyCode: {code}')
        if code in seen:
            raise ValidationAppError(f'Duplicate propertyCode: {code}')
        seen.add(code)
        require_positive_quantity(prop.numeric_value, field='numericValue')
        if get_property_unit(prop.unit.strip()) is None:
            raise ValidationAppError(f'Unsupported property unit: {prop.unit}')
        if prop.source_type not in DATA_SOURCE_TYPES:
            raise ValidationAppError('Invalid property sourceType.')
        db.add(
            CbamActivityProperty(
                organization_id=organization_id,
                activity_record_id=activity_id,
                property_code=code,
                numeric_value=prop.numeric_value,
                unit=prop.unit.strip(),
                source_type=prop.source_type,
                source_reference=prop.source_reference,
                created_by_user_id=user_id,
            )
        )


def add_activity_property(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ActivityPropertyInput,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityPropertyResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    if row.status == 'archived':
        raise BusinessRuleError('Archived activity records cannot receive properties.')
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    if row.data_source_type != 'PRIMARY':
        raise ValidationAppError(
            'Activity properties may only be supplied when dataSourceType is PRIMARY.'
        )
    _add_properties(
        db,
        organization_id=organization_id,
        activity_id=row.id,
        user_id=user.id,
        properties=[payload],
        data_source_type=row.data_source_type,
    )
    db.flush()
    prop = db.execute(
        select(CbamActivityProperty).where(
            CbamActivityProperty.activity_record_id == row.id,
            CbamActivityProperty.property_code == payload.property_code.strip(),
        )
    ).scalar_one()
    write_audit_log(
        db,
        action='cbam.activity_property.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_activity_property',
        entity_id=str(prop.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'activityRecordId': str(row.id),
            'propertyCode': prop.property_code,
            'numericValue': str(prop.numeric_value),
            'unit': prop.unit,
            'sourceType': prop.source_type,
        },
    )
    db.commit()
    db.refresh(prop)
    return ActivityPropertyResponse(
        id=prop.id,
        property_code=prop.property_code,
        numeric_value=prop.numeric_value,
        unit=prop.unit,
        source_type=prop.source_type,
        source_reference=prop.source_reference,
    )


def list_activity_records(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    activity_type: str | None = None,
    include_archived: bool = False,
) -> Page[ActivityRecordResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamActivityRecord).where(
        CbamActivityRecord.organization_id == organization_id,
        CbamActivityRecord.reporting_period_binding_id == binding_id,
    )
    if activity_type:
        stmt = stmt.where(CbamActivityRecord.activity_type == activity_type)
    if not include_archived:
        stmt = stmt.where(CbamActivityRecord.status == 'active')
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamActivityRecord.created_at.desc())
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


def get_activity_record(
    db: Session, user: User, organization_id: uuid.UUID, record_id: uuid.UUID
) -> ActivityRecordResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(db, _get_row(db, organization_id, record_id))


def create_activity_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: ActivityRecordCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityRecordResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    installation = get_installation_for_org(db, organization_id, payload.installation_profile_id)
    require_usable_installation(installation)
    activity_type, activity_group, unit = _validate_activity_and_unit(
        payload.activity_type, payload.unit
    )
    if payload.data_source_type not in DATA_SOURCE_TYPES:
        raise ValidationAppError('Invalid dataSourceType.')
    require_positive_quantity(payload.quantity)
    validate_optional_date_range(payload.period_start, payload.period_end)
    _validate_process_fields(
        activity_group,
        payload.process_type_code,
        payload.process_description,
        payload.biogenic_status,
    )
    row = CbamActivityRecord(
        organization_id=organization_id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        activity_group=activity_group,
        activity_type=activity_type,
        activity_date=payload.activity_date,
        period_start=payload.period_start,
        period_end=payload.period_end,
        quantity=payload.quantity,
        unit=unit,
        data_source_type=payload.data_source_type,
        source_reference=payload.source_reference,
        measurement_method=payload.measurement_method,
        supplier_name=payload.supplier_name,
        certificate_reference=payload.certificate_reference,
        process_type_code=payload.process_type_code,
        process_description=payload.process_description,
        biogenic_status=payload.biogenic_status,
        notes=payload.notes,
        status='active',
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    _add_properties(
        db,
        organization_id=organization_id,
        activity_id=row.id,
        user_id=user.id,
        properties=payload.properties,
        data_source_type=payload.data_source_type,
    )
    write_audit_log(
        db,
        action='cbam.activity_record.created',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_activity_record',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            'bindingId': str(binding.id),
            'activityType': row.activity_type,
            'dataSourceType': row.data_source_type,
            'quantity': str(row.quantity),
            'unit': row.unit,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def update_activity_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ActivityRecordUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityRecordResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    if row.status == 'archived':
        raise BusinessRuleError('Archived activity records cannot be updated.')
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM activity record')
    data = payload.model_dump(exclude_unset=True, exclude={'row_version'})
    if 'quantity' in data and data['quantity'] is not None:
        require_positive_quantity(data['quantity'])
        row.quantity = data['quantity']
    if 'unit' in data and data['unit'] is not None:
        _, _, unit = _validate_activity_and_unit(row.activity_type, data['unit'])
        row.unit = unit
    if 'data_source_type' in data and data['data_source_type'] is not None:
        if data['data_source_type'] not in DATA_SOURCE_TYPES:
            raise ValidationAppError('Invalid dataSourceType.')
        row.data_source_type = data['data_source_type']
    for field in (
        'activity_date',
        'period_start',
        'period_end',
        'source_reference',
        'measurement_method',
        'supplier_name',
        'certificate_reference',
        'process_type_code',
        'process_description',
        'biogenic_status',
        'notes',
    ):
        if field in data:
            setattr(row, field, data[field])
    validate_optional_date_range(row.period_start, row.period_end)
    _validate_process_fields(
        row.activity_group,
        row.process_type_code,
        row.process_description,
        row.biogenic_status,
    )
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.activity_record.updated',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_activity_record',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'fields': list(data.keys()), 'rowVersion': row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def archive_activity_record(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ActivityRecordVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ActivityRecordResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity='CBAM activity record')
    if row.status == 'archived':
        raise BusinessRuleError('Activity record is already archived.')
    row.status = 'archived'
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action='cbam.activity_record.archived',
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type='cbam_activity_record',
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={'to': 'archived'},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)
