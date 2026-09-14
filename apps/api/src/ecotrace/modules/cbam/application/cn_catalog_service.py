"""Read-only CN-code catalog resolution (Phase 6A)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError
from ecotrace.modules.cbam.application.cn_catalog_seed import (
    ensure_platform_cn_catalog,
    load_cn_catalog_seed_payload,
)
from ecotrace.modules.cbam.application.field_applicability import (
    FieldApplicability,
    field_applicability_for_cn,
)
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.infrastructure.models import (
    CbamCnCode,
    CbamCnCodeDataset,
    CbamCnControlledListValue,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate


def normalize_cn_code(value: str) -> str:
    return value.strip().replace(" ", "")


class CnCodeDatasetResponse(CamelModel):
    id: uuid.UUID
    dataset_code: str
    dataset_version: str
    content_checksum: str
    source_workbook_name: str
    source_workbook_sha256: str
    source_template_version: str
    valid_from: date
    valid_until: date | None
    status: str


class CnCodeResponse(CamelModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    cn_key: str
    normalized_code: str
    display_code: str
    description_en: str
    cbam_sector: str
    numbering_label: str | None
    source_sheet: str
    source_row: int
    status: str
    dataset_code: str
    dataset_version: str
    content_checksum: str
    field_applicability: FieldApplicability


class ControlledListValueResponse(CamelModel):
    list_code: str
    value_code: str
    value_label: str
    sort_order: int


def _dataset_to_response(row: CbamCnCodeDataset) -> CnCodeDatasetResponse:
    return CnCodeDatasetResponse(
        id=row.id,
        dataset_code=row.dataset_code,
        dataset_version=row.dataset_version,
        content_checksum=row.content_checksum,
        source_workbook_name=row.source_workbook_name,
        source_workbook_sha256=row.source_workbook_sha256,
        source_template_version=row.source_template_version,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        status=row.status,
    )


def _code_to_response(code: CbamCnCode, dataset: CbamCnCodeDataset) -> CnCodeResponse:
    return CnCodeResponse(
        id=code.id,
        dataset_id=code.dataset_id,
        cn_key=code.cn_key,
        normalized_code=code.normalized_code,
        display_code=code.display_code,
        description_en=code.description_en,
        cbam_sector=code.cbam_sector,
        numbering_label=code.numbering_label,
        source_sheet=code.source_sheet,
        source_row=code.source_row,
        status=code.status,
        dataset_code=dataset.dataset_code,
        dataset_version=dataset.dataset_version,
        content_checksum=dataset.content_checksum,
        field_applicability=FieldApplicability.from_raw(field_applicability_for_cn(code)),
    )


def get_active_cn_dataset(db: Session) -> CbamCnCodeDataset:
    row = (
        db.execute(
            select(CbamCnCodeDataset)
            .where(
                CbamCnCodeDataset.status == "ACTIVE",
                CbamCnCodeDataset.dataset_code == "CBAM_SEE_CN_CODES",
            )
            .order_by(CbamCnCodeDataset.valid_from.desc(), CbamCnCodeDataset.dataset_version.desc())
        )
        .scalars()
        .first()
    )
    if row is None:
        ensure_platform_cn_catalog(db)
        row = (
            db.execute(
                select(CbamCnCodeDataset)
                .where(
                    CbamCnCodeDataset.status == "ACTIVE",
                    CbamCnCodeDataset.dataset_code == "CBAM_SEE_CN_CODES",
                )
                .order_by(
                    CbamCnCodeDataset.valid_from.desc(),
                    CbamCnCodeDataset.dataset_version.desc(),
                )
            )
            .scalars()
            .first()
        )
    if row is None:
        raise NotFoundError("Active CN-code dataset not found.")
    return row


def list_cn_codes(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
    q: str | None = None,
    sector: str | None = None,
    include_inactive: bool = False,
) -> Page[CnCodeResponse]:
    require_cbam_view(db, user, organization_id)
    dataset = get_active_cn_dataset(db)
    stmt = select(CbamCnCode).where(CbamCnCode.dataset_id == dataset.id)
    if not include_inactive:
        stmt = stmt.where(CbamCnCode.status == "ACTIVE")
    if sector:
        stmt = stmt.where(CbamCnCode.cbam_sector == sector.strip())
    if q:
        needle = f"%{q.strip()}%"
        normalized_q = normalize_cn_code(q)
        stmt = stmt.where(
            or_(
                CbamCnCode.normalized_code.ilike(f"%{normalized_q}%"),
                CbamCnCode.display_code.ilike(needle),
                CbamCnCode.description_en.ilike(needle),
                CbamCnCode.cn_key.ilike(needle),
            )
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(CbamCnCode.normalized_code.asc(), CbamCnCode.cn_key.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_code_to_response(row, dataset) for row in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def get_cn_code(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    cn_code_id: uuid.UUID,
) -> CnCodeResponse:
    require_cbam_view(db, user, organization_id)
    code = db.get(CbamCnCode, cn_code_id)
    if code is None:
        raise NotFoundError("CN code not found.")
    dataset = db.get(CbamCnCodeDataset, code.dataset_id)
    if dataset is None:
        raise NotFoundError("CN code dataset not found.")
    return _code_to_response(code, dataset)


def resolve_cn_code(
    db: Session,
    *,
    code: str,
    dataset: CbamCnCodeDataset | None = None,
    allow_inactive: bool = False,
) -> CbamCnCode:
    active_dataset = dataset or get_active_cn_dataset(db)
    normalized = normalize_cn_code(code)
    display = code.strip()
    stmt = select(CbamCnCode).where(
        CbamCnCode.dataset_id == active_dataset.id,
        or_(
            CbamCnCode.normalized_code == normalized,
            CbamCnCode.display_code == display,
        ),
    )
    if not allow_inactive:
        stmt = stmt.where(CbamCnCode.status == "ACTIVE")
    rows = list(db.execute(stmt).scalars().all())
    if not rows:
        raise NotFoundError("CN code not found.")
    # Same logical code via display vs normalized is fine if one row.
    unique_ids = {row.id for row in rows}
    if len(unique_ids) > 1:
        raise BusinessRuleError(
            "More than one CN code matches this value. Choose a more specific code.",
            details=[{"code": "AMBIGUOUS_CN_CODE"}],
        )
    return rows[0]


def list_controlled_list_values(
    db: Session,
    *,
    list_code: str,
    dataset: CbamCnCodeDataset | None = None,
) -> list[ControlledListValueResponse]:
    active_dataset = dataset or get_active_cn_dataset(db)
    rows = list(
        db.execute(
            select(CbamCnControlledListValue)
            .where(
                CbamCnControlledListValue.dataset_id == active_dataset.id,
                CbamCnControlledListValue.list_code == list_code,
                CbamCnControlledListValue.status == "ACTIVE",
            )
            .order_by(
                CbamCnControlledListValue.sort_order.asc(),
                CbamCnControlledListValue.value_code.asc(),
            )
        )
        .scalars()
        .all()
    )
    return [
        ControlledListValueResponse(
            list_code=row.list_code,
            value_code=row.value_code,
            value_label=row.value_label,
            sort_order=row.sort_order,
        )
        for row in rows
    ]


def sector_special_parameters() -> dict[str, Any]:
    raw = load_cn_catalog_seed_payload().get("sectorSpecialParameters", {})
    return raw if isinstance(raw, dict) else {}
