from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.application.catalogs import (
    EMBEDDED_EMISSION_SOURCE_TYPES,
    require_unit,
    same_unit_family,
)
from ecotrace.modules.cbam.application.collection_guards import (
    get_binding_for_org,
    get_installation_for_org,
    get_product_profile_for_org,
    require_non_negative,
    require_positive_quantity,
    require_usable_installation,
    require_writable_binding,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import CbamPurchasedInputRecord
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


class PurchasedInputCreate(CamelModel):
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None = None
    input_name: str
    supplier_name: str | None = None
    quantity: Decimal
    unit: str
    received_date: date | None = None
    consumed_quantity: Decimal | None = None
    consumed_unit: str | None = None
    embedded_emission_value: Decimal | None = None
    embedded_emission_unit: str | None = None
    embedded_emission_source_type: str = "NOT_PROVIDED"
    source_reference: str | None = None
    notes: str | None = None


class PurchasedInputUpdate(CamelModel):
    row_version: int
    product_profile_version_id: uuid.UUID | None = None
    input_name: str | None = None
    supplier_name: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    received_date: date | None = None
    consumed_quantity: Decimal | None = None
    consumed_unit: str | None = None
    embedded_emission_value: Decimal | None = None
    embedded_emission_unit: str | None = None
    embedded_emission_source_type: str | None = None
    source_reference: str | None = None
    notes: str | None = None


class PurchasedInputVersionRequest(CamelModel):
    row_version: int


class PurchasedInputResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    reporting_period_binding_id: uuid.UUID
    installation_profile_id: uuid.UUID
    product_profile_version_id: uuid.UUID | None
    input_name: str
    supplier_name: str | None
    quantity: Decimal
    unit: str
    received_date: date | None
    consumed_quantity: Decimal | None
    consumed_unit: str | None
    embedded_emission_value: Decimal | None
    embedded_emission_unit: str | None
    embedded_emission_source_type: str
    source_reference: str | None
    notes: str | None
    status: str
    row_version: int


def _to_response(row: CbamPurchasedInputRecord) -> PurchasedInputResponse:
    return PurchasedInputResponse.model_validate(row)


def _get_row(
    db: Session, organization_id: uuid.UUID, record_id: uuid.UUID
) -> CbamPurchasedInputRecord:
    row = db.get(CbamPurchasedInputRecord, record_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("CBAM purchased input record not found.")
    return row


def _validate_consumed(
    quantity: Decimal,
    unit: str,
    consumed_quantity: Decimal | None,
    consumed_unit: str | None,
) -> tuple[Decimal | None, str | None]:
    if consumed_quantity is None and consumed_unit is None:
        return None, None
    if consumed_quantity is None or consumed_unit is None:
        raise ValidationAppError("consumedQuantity and consumedUnit must be provided together.")
    require_non_negative(consumed_quantity, field="consumedQuantity")
    consumed_unit = require_unit(consumed_unit)
    if not same_unit_family(unit, consumed_unit):
        raise BusinessRuleError(
            "consumedUnit must exactly match purchased unit for Phase 3 "
            "(unit conversion and stock accounting are BLOCKED — B-09/B-10).",
            details=[{"code": "BLOCKED_DOMAIN", "decision": "B-09"}],
        )
    if consumed_quantity > quantity:
        raise ValidationAppError(
            "consumedQuantity cannot exceed purchased quantity when units match.",
            details=[{"field": "consumedQuantity", "message": "Must be <= quantity."}],
        )
    return consumed_quantity, consumed_unit


def _validate_embedded(
    value: Decimal | None,
    unit: str | None,
    source_type: str,
) -> None:
    if source_type not in EMBEDDED_EMISSION_SOURCE_TYPES:
        raise ValidationAppError("Invalid embeddedEmissionSourceType.")
    if value is None:
        if source_type == "PRIMARY":
            raise ValidationAppError(
                "embeddedEmissionValue is required when source type is PRIMARY."
            )
        return
    require_positive_quantity(value, field="embeddedEmissionValue")
    if not unit or not unit.strip():
        raise ValidationAppError("embeddedEmissionUnit is required when a value is supplied.")


def list_purchased_inputs(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    include_archived: bool = False,
) -> Page[PurchasedInputResponse]:
    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    stmt = select(CbamPurchasedInputRecord).where(
        CbamPurchasedInputRecord.organization_id == organization_id,
        CbamPurchasedInputRecord.reporting_period_binding_id == binding_id,
    )
    if not include_archived:
        stmt = stmt.where(CbamPurchasedInputRecord.status == "active")
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamPurchasedInputRecord.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_to_response(r) for r in rows], page=page, page_size=page_size, total_items=int(total)
    )


def get_purchased_input(
    db: Session, user: User, organization_id: uuid.UUID, record_id: uuid.UUID
) -> PurchasedInputResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(_get_row(db, organization_id, record_id))


def create_purchased_input(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    payload: PurchasedInputCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedInputResponse:
    require_cbam_configure(db, user, organization_id)
    binding = get_binding_for_org(db, organization_id, binding_id)
    require_writable_binding(binding)
    installation = get_installation_for_org(db, organization_id, payload.installation_profile_id)
    require_usable_installation(installation)
    product_profile_id = payload.product_profile_version_id
    if product_profile_id is not None:
        get_product_profile_for_org(db, organization_id, product_profile_id)
    name = payload.input_name.strip()
    if not name:
        raise ValidationAppError("inputName is required.")
    require_positive_quantity(payload.quantity)
    unit = require_unit(payload.unit)
    consumed_qty, consumed_unit = _validate_consumed(
        payload.quantity, unit, payload.consumed_quantity, payload.consumed_unit
    )
    _validate_embedded(
        payload.embedded_emission_value,
        payload.embedded_emission_unit,
        payload.embedded_emission_source_type,
    )
    row = CbamPurchasedInputRecord(
        organization_id=organization_id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        product_profile_version_id=product_profile_id,
        input_name=name,
        supplier_name=payload.supplier_name,
        quantity=payload.quantity,
        unit=unit,
        received_date=payload.received_date,
        consumed_quantity=consumed_qty,
        consumed_unit=consumed_unit,
        embedded_emission_value=payload.embedded_emission_value,
        embedded_emission_unit=(
            payload.embedded_emission_unit.strip() if payload.embedded_emission_unit else None
        ),
        embedded_emission_source_type=payload.embedded_emission_source_type,
        source_reference=payload.source_reference,
        notes=payload.notes,
        status="active",
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cbam.purchased_input.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_purchased_input_record",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "bindingId": str(binding.id),
            "inputName": row.input_name,
            "quantity": str(row.quantity),
            "consumedQuantity": str(row.consumed_quantity) if row.consumed_quantity else None,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def update_purchased_input(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: PurchasedInputUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedInputResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    if row.status == "archived":
        raise BusinessRuleError("Archived purchased input records cannot be updated.")
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity="CBAM purchased input record")
    data = payload.model_dump(exclude_unset=True, exclude={"row_version"})
    if "product_profile_version_id" in data:
        pid = data["product_profile_version_id"]
        if pid is not None:
            get_product_profile_for_org(db, organization_id, pid)
        row.product_profile_version_id = pid
    if "input_name" in data and data["input_name"] is not None:
        name = data["input_name"].strip()
        if not name:
            raise ValidationAppError("inputName cannot be empty.")
        row.input_name = name
    if "quantity" in data and data["quantity"] is not None:
        require_positive_quantity(data["quantity"])
        row.quantity = data["quantity"]
    if "unit" in data and data["unit"] is not None:
        row.unit = require_unit(data["unit"])
    for field in (
        "supplier_name",
        "received_date",
        "source_reference",
        "notes",
        "embedded_emission_value",
        "embedded_emission_unit",
        "embedded_emission_source_type",
        "consumed_quantity",
        "consumed_unit",
    ):
        if field in data:
            setattr(row, field, data[field])
    consumed_qty, consumed_unit = _validate_consumed(
        row.quantity, row.unit, row.consumed_quantity, row.consumed_unit
    )
    row.consumed_quantity = consumed_qty
    row.consumed_unit = consumed_unit
    _validate_embedded(
        row.embedded_emission_value,
        row.embedded_emission_unit,
        row.embedded_emission_source_type,
    )
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.purchased_input.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_purchased_input_record",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"fields": list(data.keys()), "rowVersion": row.row_version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)


def archive_purchased_input(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: PurchasedInputVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> PurchasedInputResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, record_id)
    binding = get_binding_for_org(db, organization_id, row.reporting_period_binding_id)
    require_writable_binding(binding)
    check_row_version(row.row_version, payload.row_version, entity="CBAM purchased input record")
    if row.status == "archived":
        raise BusinessRuleError("Purchased input record is already archived.")
    row.status = "archived"
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.purchased_input.archived",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_purchased_input_record",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"to": "archived"},
    )
    db.commit()
    db.refresh(row)
    return _to_response(row)
