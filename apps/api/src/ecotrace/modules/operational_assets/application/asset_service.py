from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from ecotrace.core.ops_constants import DATA_SOURCE_TYPES, EQUIPMENT_TYPES
from ecotrace.modules.facilities.application.facility_service import get_facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.operational_assets.infrastructure.models import (
    DataSource,
    Equipment,
    ProductionLine,
)
from ecotrace.modules.reference_data.application.unit_conversion import get_unit
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.application.org_access import ensure_org_access, require_manage_structure
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class ProductionLineCreate(CamelModel):
    code: str
    name: str
    description: str | None = None
    production_category: str | None = None
    capacity_value: Decimal | None = None
    capacity_unit_code: str | None = None
    is_active: bool = True


class ProductionLineUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    production_category: str | None = None
    capacity_value: Decimal | None = None
    capacity_unit_code: str | None = None
    is_active: bool | None = None


class ProductionLineResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    code: str
    name: str
    description: str | None
    production_category: str | None
    capacity_value: Decimal | None
    capacity_unit_code: str | None
    is_active: bool


class EquipmentCreate(CamelModel):
    facility_id: uuid.UUID
    production_line_id: uuid.UUID | None = None
    code: str
    name: str
    description: str | None = None
    equipment_type: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    commissioning_date: date | None = None
    decommissioning_date: date | None = None
    is_active: bool = True
    metadata_json: dict[str, Any] | None = None


class EquipmentUpdate(CamelModel):
    production_line_id: uuid.UUID | None = None
    name: str | None = None
    description: str | None = None
    equipment_type: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    commissioning_date: date | None = None
    decommissioning_date: date | None = None
    is_active: bool | None = None
    metadata_json: dict[str, Any] | None = None


class EquipmentResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID
    production_line_id: uuid.UUID | None
    code: str
    name: str
    description: str | None
    equipment_type: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    commissioning_date: date | None
    decommissioning_date: date | None
    is_active: bool
    metadata_json: dict[str, Any] | None


class DataSourceCreate(CamelModel):
    facility_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    code: str
    name: str
    source_type: str
    description: str | None = None
    external_reference: str | None = None
    is_active: bool = True


class DataSourceUpdate(CamelModel):
    facility_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    name: str | None = None
    source_type: str | None = None
    description: str | None = None
    external_reference: str | None = None
    is_active: bool | None = None


class DataSourceResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    facility_id: uuid.UUID | None
    equipment_id: uuid.UUID | None
    code: str
    name: str
    source_type: str
    description: str | None
    external_reference: str | None
    is_active: bool
    integration_note: str | None = None


def _audit(
    db: Session,
    *,
    action: str,
    user: User,
    org_id: uuid.UUID,
    entity_type: str,
    entity_id: uuid.UUID,
    request_id: str | None,
    ip: str | None,
    ua: str | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    write_audit_log(
        db,
        action=action,
        actor_user_id=user.id,
        organization_id=org_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        request_id=request_id,
        ip_address=ip,
        user_agent=ua,
        metadata=metadata,
    )


def get_production_line(
    db: Session, organization_id: uuid.UUID, line_id: uuid.UUID
) -> ProductionLine:
    line = db.get(ProductionLine, line_id)
    if line is None or line.organization_id != organization_id:
        raise NotFoundError("Production line not found.")
    return line


def list_production_lines(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    facility_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[ProductionLineResponse]:
    ensure_org_access(db, user, organization_id)
    facility = get_facility(db, organization_id, facility_id)
    stmt = select(ProductionLine).where(
        ProductionLine.organization_id == organization_id,
        ProductionLine.facility_id == facility.id,
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(ProductionLine.name).offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [ProductionLineResponse.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def create_production_line(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    facility_id: uuid.UUID,
    payload: ProductionLineCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionLineResponse:
    require_manage_structure(db, user, organization_id)
    facility = get_facility(db, organization_id, facility_id)
    if not facility.is_active:
        raise ValidationAppError("Inactive facilities cannot receive new production lines.")
    if payload.capacity_value is not None and payload.capacity_value <= 0:
        raise ValidationAppError("Capacity must be positive.")
    if payload.capacity_unit_code:
        get_unit(db, payload.capacity_unit_code)
    code = payload.code.strip()
    if db.execute(
        select(ProductionLine.id).where(
            ProductionLine.facility_id == facility_id, ProductionLine.code == code
        )
    ).scalar_one_or_none():
        raise ConflictError("A production line with this code already exists in the facility.")
    line = ProductionLine(
        organization_id=organization_id,
        facility_id=facility_id,
        code=code,
        name=payload.name.strip(),
        description=payload.description,
        production_category=payload.production_category,
        capacity_value=payload.capacity_value,
        capacity_unit_code=payload.capacity_unit_code,
        is_active=payload.is_active,
    )
    db.add(line)
    db.flush()
    _audit(
        db,
        action="production_line.created",
        user=user,
        org_id=organization_id,
        entity_type="production_line",
        entity_id=line.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
        metadata={"code": code},
    )
    db.commit()
    db.refresh(line)
    return ProductionLineResponse.model_validate(line)


def update_production_line(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: ProductionLineUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionLineResponse:
    require_manage_structure(db, user, organization_id)
    line = get_production_line(db, organization_id, line_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("capacity_value") is not None and data["capacity_value"] <= 0:
        raise ValidationAppError("Capacity must be positive.")
    if data.get("capacity_unit_code"):
        get_unit(db, data["capacity_unit_code"])
    for k, v in data.items():
        setattr(line, k, v)
    _audit(
        db,
        action="production_line.updated",
        user=user,
        org_id=organization_id,
        entity_type="production_line",
        entity_id=line.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(line)
    return ProductionLineResponse.model_validate(line)


def archive_production_line(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    line_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductionLineResponse:
    require_manage_structure(db, user, organization_id)
    line = get_production_line(db, organization_id, line_id)
    line.is_active = False
    _audit(
        db,
        action="production_line.archived",
        user=user,
        org_id=organization_id,
        entity_type="production_line",
        entity_id=line.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
    )
    db.commit()
    db.refresh(line)
    return ProductionLineResponse.model_validate(line)


def get_equipment(db: Session, organization_id: uuid.UUID, equipment_id: uuid.UUID) -> Equipment:
    row = db.get(Equipment, equipment_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("Equipment not found.")
    return row


def list_equipment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    facility_id: uuid.UUID | None = None,
    production_line_id: uuid.UUID | None = None,
    equipment_type: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> Page[EquipmentResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(Equipment).where(Equipment.organization_id == organization_id)
    if facility_id:
        stmt = stmt.where(Equipment.facility_id == facility_id)
    if production_line_id:
        stmt = stmt.where(Equipment.production_line_id == production_line_id)
    if equipment_type:
        stmt = stmt.where(Equipment.equipment_type == equipment_type)
    if is_active is not None:
        stmt = stmt.where(Equipment.is_active.is_(is_active))
    if search:
        like = f"%{search.strip()}%"
        stmt = stmt.where(or_(Equipment.name.ilike(like), Equipment.code.ilike(like)))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(stmt.order_by(Equipment.name).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return paginate(
        [EquipmentResponse.model_validate(r) for r in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def create_equipment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: EquipmentCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> EquipmentResponse:
    require_manage_structure(db, user, organization_id)
    facility = get_facility(db, organization_id, payload.facility_id)
    if payload.equipment_type not in EQUIPMENT_TYPES:
        raise ValidationAppError("Invalid equipment type.")
    if (
        payload.decommissioning_date
        and payload.commissioning_date
        and payload.decommissioning_date < payload.commissioning_date
    ):
        raise ValidationAppError("Decommissioning date cannot be earlier than commissioning date.")
    if payload.production_line_id:
        line = get_production_line(db, organization_id, payload.production_line_id)
        if line.facility_id != facility.id:
            raise ValidationAppError("Production line must belong to the selected facility.")
    code = payload.code.strip()
    if db.execute(
        select(Equipment.id).where(Equipment.facility_id == facility.id, Equipment.code == code)
    ).scalar_one_or_none():
        raise ConflictError("Equipment code already exists in the facility.")
    row = Equipment(
        organization_id=organization_id,
        facility_id=facility.id,
        production_line_id=payload.production_line_id,
        code=code,
        name=payload.name.strip(),
        description=payload.description,
        equipment_type=payload.equipment_type,
        manufacturer=payload.manufacturer,
        model=payload.model,
        serial_number=payload.serial_number,
        commissioning_date=payload.commissioning_date,
        decommissioning_date=payload.decommissioning_date,
        is_active=payload.is_active,
        metadata_json=payload.metadata_json,
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        action="equipment.created",
        user=user,
        org_id=organization_id,
        entity_type="equipment",
        entity_id=row.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
        metadata={"code": code},
    )
    db.commit()
    db.refresh(row)
    return EquipmentResponse.model_validate(row)


def update_equipment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    equipment_id: uuid.UUID,
    payload: EquipmentUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> EquipmentResponse:
    require_manage_structure(db, user, organization_id)
    row = get_equipment(db, organization_id, equipment_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("equipment_type") and data["equipment_type"] not in EQUIPMENT_TYPES:
        raise ValidationAppError("Invalid equipment type.")
    start = data.get("commissioning_date", row.commissioning_date)
    end = data.get("decommissioning_date", row.decommissioning_date)
    if start and end and end < start:
        raise ValidationAppError("Decommissioning date cannot be earlier than commissioning date.")
    if data.get("production_line_id"):
        line = get_production_line(db, organization_id, data["production_line_id"])
        if line.facility_id != row.facility_id:
            raise ValidationAppError("Production line must belong to the selected facility.")
    for k, v in data.items():
        setattr(row, k, v)
    _audit(
        db,
        action="equipment.updated",
        user=user,
        org_id=organization_id,
        entity_type="equipment",
        entity_id=row.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(row)
    return EquipmentResponse.model_validate(row)


def archive_equipment(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    equipment_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> EquipmentResponse:
    require_manage_structure(db, user, organization_id)
    row = get_equipment(db, organization_id, equipment_id)
    row.is_active = False
    _audit(
        db,
        action="equipment.archived",
        user=user,
        org_id=organization_id,
        entity_type="equipment",
        entity_id=row.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
    )
    db.commit()
    db.refresh(row)
    return EquipmentResponse.model_validate(row)


def data_source_response(row: DataSource) -> DataSourceResponse:
    note = None
    if row.source_type in {"api", "mqtt", "erp", "scada"}:
        note = "Integration is planned for a later phase."
    data = DataSourceResponse.model_validate(row)
    data.integration_note = note
    return data


def _ds_response(row: DataSource) -> DataSourceResponse:
    return data_source_response(row)


def get_data_source(
    db: Session, organization_id: uuid.UUID, data_source_id: uuid.UUID
) -> DataSource:
    row = db.get(DataSource, data_source_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("Data source not found.")
    return row


def list_data_sources(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> Page[DataSourceResponse]:
    ensure_org_access(db, user, organization_id)
    stmt = select(DataSource).where(DataSource.organization_id == organization_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(stmt.order_by(DataSource.name).offset((page - 1) * page_size).limit(page_size))
        .scalars()
        .all()
    )
    return paginate(
        [_ds_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def create_data_source(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: DataSourceCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DataSourceResponse:
    require_manage_structure(db, user, organization_id)
    if payload.source_type not in DATA_SOURCE_TYPES:
        raise ValidationAppError("Invalid source type.")
    if payload.facility_id:
        get_facility(db, organization_id, payload.facility_id)
    if payload.equipment_id:
        eq = get_equipment(db, organization_id, payload.equipment_id)
        if payload.facility_id and eq.facility_id != payload.facility_id:
            raise ValidationAppError("Equipment must belong to the selected facility.")
    code = payload.code.strip()
    if db.execute(
        select(DataSource.id).where(
            DataSource.organization_id == organization_id, DataSource.code == code
        )
    ).scalar_one_or_none():
        raise ConflictError("Data source code already exists in the organization.")
    row = DataSource(
        organization_id=organization_id,
        facility_id=payload.facility_id,
        equipment_id=payload.equipment_id,
        code=code,
        name=payload.name.strip(),
        source_type=payload.source_type,
        description=payload.description,
        external_reference=payload.external_reference,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        action="data_source.created",
        user=user,
        org_id=organization_id,
        entity_type="data_source",
        entity_id=row.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
        metadata={"code": code},
    )
    db.commit()
    db.refresh(row)
    return _ds_response(row)


def update_data_source(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    data_source_id: uuid.UUID,
    payload: DataSourceUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DataSourceResponse:
    require_manage_structure(db, user, organization_id)
    row = get_data_source(db, organization_id, data_source_id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("source_type") and data["source_type"] not in DATA_SOURCE_TYPES:
        raise ValidationAppError("Invalid source type.")
    for k, v in data.items():
        setattr(row, k, v)
    _audit(
        db,
        action="data_source.updated",
        user=user,
        org_id=organization_id,
        entity_type="data_source",
        entity_id=row.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
        metadata={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(row)
    return _ds_response(row)


def archive_data_source(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    data_source_id: uuid.UUID,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> DataSourceResponse:
    require_manage_structure(db, user, organization_id)
    row = get_data_source(db, organization_id, data_source_id)
    row.is_active = False
    _audit(
        db,
        action="data_source.archived",
        user=user,
        org_id=organization_id,
        entity_type="data_source",
        entity_id=row.id,
        request_id=request_id,
        ip=ip_address,
        ua=user_agent,
    )
    db.commit()
    db.refresh(row)
    return _ds_response(row)
