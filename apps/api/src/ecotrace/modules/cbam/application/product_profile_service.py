"""CBAM product-profile versions with computed classification readiness (Phase 6A)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import (
    BusinessRuleError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.modules.cbam.application.cn_catalog_service import (
    get_active_cn_dataset,
    list_controlled_list_values,
    resolve_cn_code,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.field_applicability import (
    FIELD_ATTR_BY_KEY,
    FieldApplicability,
    clear_non_applicable_special_fields,
    collect_non_applicable_write_errors,
    empty_field_applicability,
    field_applicability_for_cn,
    normalize_field_applicability,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_configure, require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamCnCode,
    CbamCnCodeDataset,
    CbamProductProfileVersion,
)
from ecotrace.modules.cbam.infrastructure.product_reference_adapter import (
    require_product_in_organization,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.application.audit import write_audit_log
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

PERCENT_TOLERANCE = Decimal("0.00000001")
PERCENT_FIELDS = (
    "percent_mn",
    "percent_cr",
    "percent_ni",
    "percent_other_alloys",
    "percent_other_materials",
)
SPECIAL_WRITE_ATTRS = tuple(FIELD_ATTR_BY_KEY.values())


class ProductProfileCreate(CamelModel):
    product_id: uuid.UUID
    product_name: str | None = None
    cn_code: str | None = None
    reducing_agent: str | None = None
    steel_mill_identification_number: str | None = None
    percent_mn: Decimal | None = None
    percent_cr: Decimal | None = None
    percent_ni: Decimal | None = None
    percent_other_alloys: Decimal | None = None
    percent_other_materials: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    # Explicitly rejected if true — readiness is server-computed only.
    classification_ready: bool | None = None


class ProductProfileUpdate(CamelModel):
    row_version: int
    product_name: str | None = None
    cn_code: str | None = None
    reducing_agent: str | None = None
    steel_mill_identification_number: str | None = None
    percent_mn: Decimal | None = None
    percent_cr: Decimal | None = None
    percent_ni: Decimal | None = None
    percent_other_alloys: Decimal | None = None
    percent_other_materials: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    classification_ready: bool | None = None


class ProductProfileVersionRequest(CamelModel):
    row_version: int


class ProductProfileIssue(CamelModel):
    code: str
    message: str


class ProductProfileResponse(CamelModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    product_id: uuid.UUID
    version: int
    status: str
    valid_from: date | None
    valid_to: date | None
    classification_ready: bool
    product_name: str | None
    cn_code_id: uuid.UUID | None
    cn_normalized_code: str | None
    cn_display_code: str | None
    cn_description: str | None
    cn_sector: str | None
    cn_dataset_code: str | None
    cn_dataset_version: str | None
    field_applicability: FieldApplicability
    reducing_agent: str | None
    steel_mill_identification_number: str | None
    percent_mn: Decimal | None
    percent_cr: Decimal | None
    percent_ni: Decimal | None
    percent_other_alloys: Decimal | None
    percent_other_materials: Decimal | None
    missing_requirements: list[ProductProfileIssue]
    validation_issues: list[ProductProfileIssue]
    row_version: int


def reject_classification_ready_true() -> None:
    raise BusinessRuleError(
        "classificationReady is calculated by the server. You cannot set it yourself.",
        details=[{"code": "CLASSIFICATION_READY_CLIENT_WRITE_FORBIDDEN"}],
    )


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _validate_percent(
    field: str,
    value: Decimal | None,
    issues: list[dict[str, str]],
) -> None:
    if value is None:
        return
    if value < 0:
        issues.append(
            _issue(
                f"{field.upper()}_BELOW_ZERO",
                f"The {field.replace('_', ' ')} must be between 0 and 100.",
            )
        )
    elif value > 100:
        issues.append(
            _issue(
                f"{field.upper()}_ABOVE_100",
                f"The {field.replace('_', ' ')} must be between 0 and 100.",
            )
        )


def compute_classification_state(
    *,
    product_name: str | None,
    cn: CbamCnCode | None,
    dataset: CbamCnCodeDataset | None,
    reducing_agent: str | None,
    steel_mill_identification_number: str | None,
    percent_mn: Decimal | None,
    percent_cr: Decimal | None,
    percent_ni: Decimal | None,
    percent_other_alloys: Decimal | None,
    percent_other_materials: Decimal | None,
    allowed_reducing_agents: set[str],
    field_applicability: dict[str, bool] | None = None,
) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
    missing: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []

    name = (product_name or "").strip()
    if not name:
        missing.append(_issue("PRODUCT_NAME_REQUIRED", "Enter a product name."))
    if cn is None or dataset is None:
        missing.append(_issue("CN_CODE_REQUIRED", "Select a valid CN code."))

    # Authoritative source: persisted CN.field_applicability (workbook-derived).
    fa = normalize_field_applicability(
        field_applicability if field_applicability is not None else field_applicability_for_cn(cn)
    )

    if fa["reducingAgent"]:
        if not (reducing_agent or "").strip():
            missing.append(
                _issue(
                    "REDUCING_AGENT_REQUIRED",
                    "Select the main reducing agent used for this steel product.",
                )
            )
        elif reducing_agent not in allowed_reducing_agents:
            issues.append(
                _issue(
                    "REDUCING_AGENT_INVALID",
                    "Choose a reducing agent from the official list.",
                )
            )
    elif reducing_agent:
        issues.append(
            _issue(
                "REDUCING_AGENT_NOT_APPLICABLE",
                "Reducing agent is not used for this CN code.",
            )
        )

    if fa["steelMillIdentificationNumber"]:
        if not (steel_mill_identification_number or "").strip():
            missing.append(
                _issue(
                    "STEEL_MILL_ID_REQUIRED",
                    "Enter the producing installation identification number.",
                )
            )
    elif steel_mill_identification_number:
        issues.append(
            _issue(
                "STEEL_MILL_ID_NOT_APPLICABLE",
                "Steel mill identification is not used for this CN code.",
            )
        )

    values = {
        "percent_mn": percent_mn,
        "percent_cr": percent_cr,
        "percent_ni": percent_ni,
        "percent_other_alloys": percent_other_alloys,
        "percent_other_materials": percent_other_materials,
    }
    applicability = {
        "percent_mn": fa["percentMn"],
        "percent_cr": fa["percentCr"],
        "percent_ni": fa["percentNi"],
        "percent_other_alloys": fa["percentOtherAlloys"],
        "percent_other_materials": fa["percentOtherMaterials"],
    }
    for field, value in values.items():
        if value is not None and not applicability[field]:
            issues.append(
                _issue(
                    f"{field.upper()}_NOT_APPLICABLE",
                    "This percentage is not used for the selected CN code.",
                )
            )
            continue
        _validate_percent(field, value, issues)

    applicable_entered = [
        value
        for field, applicable in applicability.items()
        if applicable and (value := values[field]) is not None
    ]
    applicable_fields = [field for field, applicable in applicability.items() if applicable]
    if applicable_entered:
        total = sum(applicable_entered, Decimal("0"))
        if total - Decimal("100") > PERCENT_TOLERANCE:
            issues.append(
                _issue(
                    "PERCENTAGE_SUM_ABOVE_100",
                    "The entered percentages add up to more than 100.",
                )
            )
        elif all(values[field] is not None for field in applicable_fields) and (
            abs(total - Decimal("100")) > PERCENT_TOLERANCE
        ):
            issues.append(
                _issue(
                    "PERCENTAGE_SUM_NOT_100",
                    "When all composition percentages are entered, they must add up to 100.",
                )
            )

    ready = not missing and not issues and cn is not None and bool(name)
    return ready, missing, issues


def _to_response(db: Session, row: CbamProductProfileVersion) -> ProductProfileResponse:
    def _issues(raw: Any) -> list[ProductProfileIssue]:
        if not isinstance(raw, list):
            return []
        out: list[ProductProfileIssue] = []
        for item in raw:
            if isinstance(item, dict) and "code" in item and "message" in item:
                out.append(ProductProfileIssue(code=item["code"], message=item["message"]))
        return out

    cn = db.get(CbamCnCode, row.cn_code_id) if row.cn_code_id else None
    return ProductProfileResponse(
        id=row.id,
        organization_id=row.organization_id,
        product_id=row.product_id,
        version=row.version,
        status=row.status,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        classification_ready=bool(row.classification_ready),
        product_name=row.product_name,
        cn_code_id=row.cn_code_id,
        cn_normalized_code=row.cn_normalized_code,
        cn_display_code=row.cn_display_code,
        cn_description=row.cn_description,
        cn_sector=row.cn_sector,
        cn_dataset_code=row.cn_dataset_code,
        cn_dataset_version=row.cn_dataset_version,
        field_applicability=FieldApplicability.from_raw(field_applicability_for_cn(cn)),
        reducing_agent=row.reducing_agent,
        steel_mill_identification_number=row.steel_mill_identification_number,
        percent_mn=row.percent_mn,
        percent_cr=row.percent_cr,
        percent_ni=row.percent_ni,
        percent_other_alloys=row.percent_other_alloys,
        percent_other_materials=row.percent_other_materials,
        missing_requirements=_issues(row.missing_requirements),
        validation_issues=_issues(row.validation_issues),
        row_version=row.row_version,
    )


def _get_row(
    db: Session, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> CbamProductProfileVersion:
    row = db.get(CbamProductProfileVersion, profile_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("CBAM product profile version not found.")
    return row


def _applicability_for_row(db: Session, row: CbamProductProfileVersion) -> dict[str, bool]:
    if not row.cn_code_id:
        return empty_field_applicability()
    cn = db.get(CbamCnCode, row.cn_code_id)
    return field_applicability_for_cn(cn)


def _enforce_applicability_writes(
    db: Session,
    row: CbamProductProfileVersion,
    *,
    explicit_attrs: dict[str, Any],
) -> dict[str, bool]:
    """Reject explicit non-applicable writes; clear leftover draft values for new CN."""
    fa = _applicability_for_row(db, row)
    errors = collect_non_applicable_write_errors(fa, explicit_attrs=explicit_attrs)
    if errors:
        raise ValidationAppError(
            "One or more fields are not applicable to the selected CN code.",
            details=errors,
        )
    # Draft CN-change rule: drop stale special-field values that no longer apply.
    clear_non_applicable_special_fields(row, fa)
    return fa


def _apply_readiness(db: Session, row: CbamProductProfileVersion) -> None:
    dataset = get_active_cn_dataset(db)
    cn = db.get(CbamCnCode, row.cn_code_id) if row.cn_code_id else None
    allowed = {
        item.value_code
        for item in list_controlled_list_values(db, list_code="REDUCING_AGENT", dataset=dataset)
    }
    fa = field_applicability_for_cn(cn)
    ready, missing, issues = compute_classification_state(
        product_name=row.product_name,
        cn=cn,
        dataset=dataset if cn else None,
        reducing_agent=row.reducing_agent,
        steel_mill_identification_number=row.steel_mill_identification_number,
        percent_mn=row.percent_mn,
        percent_cr=row.percent_cr,
        percent_ni=row.percent_ni,
        percent_other_alloys=row.percent_other_alloys,
        percent_other_materials=row.percent_other_materials,
        allowed_reducing_agents=allowed,
        field_applicability=fa,
    )
    row.classification_ready = ready
    row.missing_requirements = missing
    row.validation_issues = issues


def _assign_cn_snapshot(db: Session, row: CbamProductProfileVersion, cn_code: str | None) -> None:
    if cn_code is None or not str(cn_code).strip():
        row.cn_code_id = None
        row.cn_normalized_code = None
        row.cn_display_code = None
        row.cn_description = None
        row.cn_sector = None
        row.cn_dataset_code = None
        row.cn_dataset_version = None
        return
    dataset = get_active_cn_dataset(db)
    cn = resolve_cn_code(db, code=cn_code, dataset=dataset)
    row.cn_code_id = cn.id
    row.cn_normalized_code = cn.normalized_code
    row.cn_display_code = cn.display_code
    row.cn_description = cn.description_en
    row.cn_sector = cn.cbam_sector
    row.cn_dataset_code = dataset.dataset_code
    row.cn_dataset_version = dataset.dataset_version


def list_product_profiles(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    product_id: uuid.UUID | None = None,
    status: str | None = None,
) -> Page[ProductProfileResponse]:
    require_cbam_view(db, user, organization_id)
    stmt = select(CbamProductProfileVersion).where(
        CbamProductProfileVersion.organization_id == organization_id
    )
    if product_id is not None:
        stmt = stmt.where(CbamProductProfileVersion.product_id == product_id)
    if status:
        stmt = stmt.where(CbamProductProfileVersion.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamProductProfileVersion.product_id.asc(),
                CbamProductProfileVersion.version.desc(),
            )
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


def list_product_profiles_for_binding(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
) -> Page[ProductProfileResponse]:
    from ecotrace.modules.cbam.application.collection_guards import get_binding_for_org

    require_cbam_view(db, user, organization_id)
    get_binding_for_org(db, organization_id, binding_id)
    return list_product_profiles(
        db,
        user,
        organization_id,
        page=page,
        page_size=page_size,
        status=status,
    )


def get_product_profile(
    db: Session, user: User, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> ProductProfileResponse:
    require_cbam_view(db, user, organization_id)
    return _to_response(db, _get_row(db, organization_id, profile_id))


def create_product_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: ProductProfileCreate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductProfileResponse:
    require_cbam_configure(db, user, organization_id)
    if payload.classification_ready is True:
        reject_classification_ready_true()
    product = require_product_in_organization(db, organization_id, payload.product_id)
    if payload.valid_from and payload.valid_to and payload.valid_to < payload.valid_from:
        raise ValidationAppError("validTo must be on or after validFrom.")

    max_version = db.execute(
        select(func.max(CbamProductProfileVersion.version)).where(
            CbamProductProfileVersion.organization_id == organization_id,
            CbamProductProfileVersion.product_id == product.id,
        )
    ).scalar_one()
    next_version = int(max_version or 0) + 1

    explicit = payload.model_dump(exclude_unset=True)
    explicit.pop("classification_ready", None)
    explicit_special = {k: explicit[k] for k in SPECIAL_WRITE_ATTRS if k in explicit}

    row = CbamProductProfileVersion(
        organization_id=organization_id,
        product_id=product.id,
        version=next_version,
        status="draft",
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        product_name=(payload.product_name or "").strip() or None,
        reducing_agent=(payload.reducing_agent or "").strip() or None,
        steel_mill_identification_number=(
            (payload.steel_mill_identification_number or "").strip() or None
        ),
        percent_mn=payload.percent_mn,
        percent_cr=payload.percent_cr,
        percent_ni=payload.percent_ni,
        percent_other_alloys=payload.percent_other_alloys,
        percent_other_materials=payload.percent_other_materials,
        classification_ready=False,
        missing_requirements=[],
        validation_issues=[],
        row_version=1,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    _assign_cn_snapshot(db, row, payload.cn_code)
    _enforce_applicability_writes(db, row, explicit_attrs=explicit_special)
    _apply_readiness(db, row)
    db.add(row)
    db.flush()
    write_audit_log(
        db,
        action="cbam.product_profile.created",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_product_profile_version",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={
            "productId": str(row.product_id),
            "version": row.version,
            "status": row.status,
            "classificationReady": row.classification_ready,
        },
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def update_product_profile_draft(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: ProductProfileUpdate,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductProfileResponse:
    require_cbam_configure(db, user, organization_id)
    if payload.classification_ready is True:
        reject_classification_ready_true()
    row = _get_row(db, organization_id, profile_id)
    check_row_version(row.row_version, payload.row_version, entity="CBAM product profile version")
    if row.status != "draft":
        raise BusinessRuleError(
            "Only draft product profiles can be edited. Publish a new version to make changes.",
            details=[{"code": "PROFILE_NOT_DRAFT"}],
        )
    data = payload.model_dump(exclude_unset=True)
    data.pop("row_version", None)
    data.pop("classification_ready", None)
    if "product_name" in data:
        row.product_name = (data["product_name"] or "").strip() or None
    if "cn_code" in data:
        _assign_cn_snapshot(db, row, data["cn_code"])
    if "reducing_agent" in data:
        row.reducing_agent = (data["reducing_agent"] or "").strip() or None
    if "steel_mill_identification_number" in data:
        row.steel_mill_identification_number = (
            data["steel_mill_identification_number"] or ""
        ).strip() or None
    for field in PERCENT_FIELDS:
        if field in data:
            setattr(row, field, data[field])
    if "valid_from" in data:
        row.valid_from = data["valid_from"]
    if "valid_to" in data:
        row.valid_to = data["valid_to"]
    if row.valid_from and row.valid_to and row.valid_to < row.valid_from:
        raise ValidationAppError("validTo must be on or after validFrom.")

    explicit_special = {k: data[k] for k in SPECIAL_WRITE_ATTRS if k in data}
    # When only CN changes, still clear stale non-applicable values (no reject).
    _enforce_applicability_writes(db, row, explicit_attrs=explicit_special)
    _apply_readiness(db, row)
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.product_profile.updated",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_product_profile_version",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"version": row.version, "classificationReady": row.classification_ready},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def publish_product_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: ProductProfileVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductProfileResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, profile_id)
    check_row_version(row.row_version, payload.row_version, entity="CBAM product profile version")
    if row.status != "draft":
        raise BusinessRuleError(
            "Only a draft product profile can be published.",
            details=[{"code": "PROFILE_NOT_DRAFT"}],
        )
    _apply_readiness(db, row)
    if not row.classification_ready:
        raise BusinessRuleError(
            "This product profile is not ready to publish. Fix the missing or invalid fields.",
            details=[
                {"code": "PROFILE_NOT_READY"},
                {"missingRequirements": row.missing_requirements},
                {"validationIssues": row.validation_issues},
            ],
        )
    current_active = list(
        db.execute(
            select(CbamProductProfileVersion).where(
                CbamProductProfileVersion.organization_id == organization_id,
                CbamProductProfileVersion.product_id == row.product_id,
                CbamProductProfileVersion.status == "active",
                CbamProductProfileVersion.id != row.id,
            )
        )
        .scalars()
        .all()
    )
    for active in current_active:
        active.status = "superseded"
        active.updated_by_user_id = user.id
        active.row_version += 1
    row.status = "active"
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.product_profile.published",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_product_profile_version",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"version": row.version, "classificationReady": True},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)


def archive_product_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    profile_id: uuid.UUID,
    payload: ProductProfileVersionRequest,
    *,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> ProductProfileResponse:
    require_cbam_configure(db, user, organization_id)
    row = _get_row(db, organization_id, profile_id)
    check_row_version(row.row_version, payload.row_version, entity="CBAM product profile version")
    if row.status not in ("draft", "active", "superseded"):
        raise BusinessRuleError("This product profile cannot be archived.")
    previous = row.status
    row.status = "archived"
    row.updated_by_user_id = user.id
    row.row_version += 1
    write_audit_log(
        db,
        action="cbam.product_profile.archived",
        actor_user_id=user.id,
        organization_id=organization_id,
        entity_type="cbam_product_profile_version",
        entity_id=str(row.id),
        request_id=request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata={"previousStatus": previous, "version": row.version},
    )
    db.commit()
    db.refresh(row)
    return _to_response(db, row)
