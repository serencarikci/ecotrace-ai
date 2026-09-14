"""Read-only EU precursor default-value catalog search and resolution (Phase 10A)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import NotFoundError
from ecotrace.modules.cbam.application.permissions import require_cbam_view
from ecotrace.modules.cbam.application.precursor_constants import (
    CODE_DEFAULT_VALUE_AMBIGUOUS,
    CODE_DEFAULT_VALUE_UNRESOLVED,
    CODE_PRECURSOR_CN_REQUIRED,
    CODE_PRECURSOR_COUNTRY_REQUIRED,
    DEFAULT_DATASET_CODE,
    DEFAULT_DATASET_STATUS_ACTIVE,
    DV_STATUS_NUMERIC,
    OTHER_COUNTRIES_FALLBACK_NOTE,
    RESOLUTION_AMBIGUOUS,
    RESOLUTION_RESOLVED,
    RESOLUTION_UNRESOLVED,
    SPECIFIC_DIRECT_UNIT,
    SPECIFIC_INDIRECT_UNIT,
)
from ecotrace.modules.cbam.application.precursor_default_catalog_seed import (
    build_lookup_key,
    ensure_platform_precursor_default_catalog,
    normalize_lookup_segment,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamPrecursorDefaultDataset,
    CbamPrecursorDefaultValue,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.shared.domain.schemas import CamelModel, Page, paginate

MAX_RESOLUTION_CANDIDATES = 25


def normalize_precursor_cn_code(value: str) -> str:
    return re.sub(r"[^0-9]", "", value)


def normalize_country_name(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


class PrecursorDefaultDatasetResponse(CamelModel):
    id: uuid.UUID
    dataset_code: str
    dataset_version: str
    content_checksum: str
    source_workbook_name: str
    source_workbook_sha256: str
    source_template_version: str
    regulation_reference: str | None
    valid_from: date
    valid_until: date | None
    status: str
    value_count: int


class PrecursorDefaultValueResponse(CamelModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    country_name: str
    is_other_countries_group: bool
    cn_normalized_code: str
    cn_display_code: str | None
    goods_category: str | None
    goods_description: str | None
    production_route: str | None
    direct_value: Decimal | None
    direct_value_status: str
    indirect_value: Decimal | None
    indirect_value_status: str
    total_value: Decimal | None
    total_value_status: str
    direct_unit: str
    indirect_unit: str
    unit_note: str | None
    marked_up_totals: dict[str, Any]
    original_keys: dict[str, Any]
    lookup_key: str
    source_sheet: str
    source_row: int


class PrecursorDefaultResolveRequest(CamelModel):
    country_of_origin: str
    cn_code: str
    production_route: str | None = None
    goods_description: str | None = None


class PrecursorDefaultResolution(CamelModel):
    status: str
    issue_code: str | None
    lookup_key: str
    country_of_origin: str | None
    cn_normalized_code: str | None
    production_route: str | None
    goods_description: str | None
    dataset: PrecursorDefaultDatasetResponse | None
    value: PrecursorDefaultValueResponse | None
    candidate_count: int
    candidates: list[PrecursorDefaultValueResponse]
    other_countries_note: str


def _dataset_to_response(row: CbamPrecursorDefaultDataset) -> PrecursorDefaultDatasetResponse:
    return PrecursorDefaultDatasetResponse(
        id=row.id,
        dataset_code=row.dataset_code,
        dataset_version=row.dataset_version,
        content_checksum=row.content_checksum,
        source_workbook_name=row.source_workbook_name,
        source_workbook_sha256=row.source_workbook_sha256,
        source_template_version=row.source_template_version,
        regulation_reference=row.regulation_reference,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        status=row.status,
        value_count=row.value_count,
    )


def _value_to_response(row: CbamPrecursorDefaultValue) -> PrecursorDefaultValueResponse:
    return PrecursorDefaultValueResponse(
        id=row.id,
        dataset_id=row.dataset_id,
        country_name=row.country_name,
        is_other_countries_group=row.is_other_countries_group,
        cn_normalized_code=row.cn_normalized_code,
        cn_display_code=row.cn_display_code,
        goods_category=row.goods_category,
        goods_description=row.goods_description,
        production_route=row.production_route,
        direct_value=row.direct_value,
        direct_value_status=row.direct_value_status,
        indirect_value=row.indirect_value,
        indirect_value_status=row.indirect_value_status,
        total_value=row.total_value,
        total_value_status=row.total_value_status,
        direct_unit=row.direct_unit or SPECIFIC_DIRECT_UNIT,
        indirect_unit=row.indirect_unit or SPECIFIC_INDIRECT_UNIT,
        unit_note=row.unit_note,
        marked_up_totals=dict(row.marked_up_totals_json or {}),
        original_keys=dict(row.original_keys_json or {}),
        lookup_key=row.lookup_key,
        source_sheet=row.source_sheet,
        source_row=row.source_row,
    )


def _select_active_dataset() -> Select[tuple[CbamPrecursorDefaultDataset]]:
    return (
        select(CbamPrecursorDefaultDataset)
        .where(
            CbamPrecursorDefaultDataset.status == DEFAULT_DATASET_STATUS_ACTIVE,
            CbamPrecursorDefaultDataset.dataset_code == DEFAULT_DATASET_CODE,
        )
        .order_by(
            CbamPrecursorDefaultDataset.valid_from.desc(),
            CbamPrecursorDefaultDataset.dataset_version.desc(),
        )
    )


def get_active_dataset(db: Session) -> CbamPrecursorDefaultDataset:
    """Active EU default-value dataset, seeding the platform catalog on first use."""
    row = db.execute(_select_active_dataset()).scalars().first()
    if row is None:
        ensure_platform_precursor_default_catalog(db)
        row = db.execute(_select_active_dataset()).scalars().first()
    if row is None:
        raise NotFoundError("Active precursor default-value dataset not found.")
    return row


def get_active_dataset_response(
    db: Session, user: User, organization_id: uuid.UUID
) -> PrecursorDefaultDatasetResponse:
    require_cbam_view(db, user, organization_id)
    return _dataset_to_response(get_active_dataset(db))


def search_default_values(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    page: int = 1,
    page_size: int = 20,
    country: str | None = None,
    cn: str | None = None,
    route: str | None = None,
    description: str | None = None,
    q: str | None = None,
    include_other_countries_group: bool = True,
) -> Page[PrecursorDefaultValueResponse]:
    require_cbam_view(db, user, organization_id)
    dataset = get_active_dataset(db)
    stmt = select(CbamPrecursorDefaultValue).where(
        CbamPrecursorDefaultValue.dataset_id == dataset.id
    )
    if country:
        stmt = stmt.where(
            func.lower(CbamPrecursorDefaultValue.country_name)
            == normalize_country_name(country).lower()
        )
    if cn:
        normalized_cn = normalize_precursor_cn_code(cn)
        if normalized_cn:
            stmt = stmt.where(
                CbamPrecursorDefaultValue.cn_normalized_code.startswith(normalized_cn)
            )
    if route:
        stmt = stmt.where(
            func.lower(CbamPrecursorDefaultValue.production_route) == route.strip().lower()
        )
    if description:
        stmt = stmt.where(
            CbamPrecursorDefaultValue.goods_description.ilike(f"%{description.strip()}%")
        )
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                CbamPrecursorDefaultValue.goods_description.ilike(needle),
                CbamPrecursorDefaultValue.goods_category.ilike(needle),
                CbamPrecursorDefaultValue.cn_display_code.ilike(needle),
                CbamPrecursorDefaultValue.country_name.ilike(needle),
            )
        )
    if not include_other_countries_group:
        stmt = stmt.where(CbamPrecursorDefaultValue.is_other_countries_group.is_(False))

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = list(
        db.execute(
            stmt.order_by(
                CbamPrecursorDefaultValue.country_name.asc(),
                CbamPrecursorDefaultValue.cn_normalized_code.asc(),
                CbamPrecursorDefaultValue.source_row.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return paginate(
        [_value_to_response(row) for row in rows],
        page=page,
        page_size=page_size,
        total_items=int(total),
    )


def _unresolved(
    *,
    lookup_key: str,
    country: str | None,
    cn: str | None,
    route: str | None,
    description: str | None,
    dataset: CbamPrecursorDefaultDataset | None,
    issue_code: str,
    candidates: list[CbamPrecursorDefaultValue] | None = None,
    status: str = RESOLUTION_UNRESOLVED,
) -> PrecursorDefaultResolution:
    rows = candidates or []
    return PrecursorDefaultResolution(
        status=status,
        issue_code=issue_code,
        lookup_key=lookup_key,
        country_of_origin=country,
        cn_normalized_code=cn,
        production_route=route,
        goods_description=description,
        dataset=_dataset_to_response(dataset) if dataset is not None else None,
        value=None,
        candidate_count=len(rows),
        candidates=[_value_to_response(row) for row in rows[:MAX_RESOLUTION_CANDIDATES]],
        other_countries_note=OTHER_COUNTRIES_FALLBACK_NOTE,
    )


def resolve_default_value(
    db: Session,
    *,
    country_of_origin: str | None,
    cn_code: str | None,
    production_route: str | None = None,
    goods_description: str | None = None,
    dataset: CbamPrecursorDefaultDataset | None = None,
) -> PrecursorDefaultResolution:
    """Deterministic country+CN+route(+description) resolution.

    Never falls back to the "Other Countries and Territories" group and never picks an
    arbitrary row: several remaining candidates always resolve to AMBIGUOUS.
    """
    country = normalize_country_name(country_of_origin) if country_of_origin else None
    normalized_cn = normalize_precursor_cn_code(cn_code) if cn_code else None
    route = production_route.strip() if production_route and production_route.strip() else None
    description = (
        goods_description.strip() if goods_description and goods_description.strip() else None
    )
    lookup_key = build_lookup_key(
        country_name=country,
        cn_normalized_code=normalized_cn,
        production_route=route,
        goods_description=description,
    )

    if not country:
        return _unresolved(
            lookup_key=lookup_key,
            country=country,
            cn=normalized_cn,
            route=route,
            description=description,
            dataset=None,
            issue_code=CODE_PRECURSOR_COUNTRY_REQUIRED,
        )
    if not normalized_cn:
        return _unresolved(
            lookup_key=lookup_key,
            country=country,
            cn=normalized_cn,
            route=route,
            description=description,
            dataset=None,
            issue_code=CODE_PRECURSOR_CN_REQUIRED,
        )

    active = dataset or get_active_dataset(db)
    stmt = select(CbamPrecursorDefaultValue).where(
        CbamPrecursorDefaultValue.dataset_id == active.id,
        func.lower(CbamPrecursorDefaultValue.country_name) == country.lower(),
        CbamPrecursorDefaultValue.cn_normalized_code == normalized_cn,
    )
    if route is None:
        stmt = stmt.where(CbamPrecursorDefaultValue.production_route.is_(None))
    else:
        stmt = stmt.where(func.lower(CbamPrecursorDefaultValue.production_route) == route.lower())
    rows = list(
        db.execute(stmt.order_by(CbamPrecursorDefaultValue.source_row.asc())).scalars().all()
    )

    if not rows:
        return _unresolved(
            lookup_key=lookup_key,
            country=country,
            cn=normalized_cn,
            route=route,
            description=description,
            dataset=active,
            issue_code=CODE_DEFAULT_VALUE_UNRESOLVED,
        )

    if len(rows) > 1 and description is not None:
        needle = normalize_lookup_segment(description)
        narrowed = [
            row for row in rows if normalize_lookup_segment(row.goods_description) == needle
        ]
        if narrowed:
            rows = narrowed

    if len(rows) > 1:
        return _unresolved(
            lookup_key=lookup_key,
            country=country,
            cn=normalized_cn,
            route=route,
            description=description,
            dataset=active,
            issue_code=CODE_DEFAULT_VALUE_AMBIGUOUS,
            candidates=rows,
            status=RESOLUTION_AMBIGUOUS,
        )

    match = rows[0]
    return PrecursorDefaultResolution(
        status=RESOLUTION_RESOLVED,
        issue_code=None,
        lookup_key=lookup_key,
        country_of_origin=country,
        cn_normalized_code=normalized_cn,
        production_route=route,
        goods_description=description,
        dataset=_dataset_to_response(active),
        value=_value_to_response(match),
        candidate_count=1,
        candidates=[_value_to_response(match)],
        other_countries_note=OTHER_COUNTRIES_FALLBACK_NOTE,
    )


def resolve_default_value_for_org(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    payload: PrecursorDefaultResolveRequest,
) -> PrecursorDefaultResolution:
    require_cbam_view(db, user, organization_id)
    return resolve_default_value(
        db,
        country_of_origin=payload.country_of_origin,
        cn_code=payload.cn_code,
        production_route=payload.production_route,
        goods_description=payload.goods_description,
    )


def _decimal_str(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def build_default_snapshot(
    *,
    dataset: CbamPrecursorDefaultDataset,
    value: CbamPrecursorDefaultValue,
    lookup_key: str,
    requested_country: str | None,
    requested_cn: str | None,
    requested_route: str | None,
    requested_description: str | None,
) -> dict[str, Any]:
    """Immutable per-record snapshot. Historical reads never re-query the catalog."""
    return {
        "snapshotVersion": 1,
        "resolvedAt": datetime.now(UTC).isoformat(),
        "dataset": {
            "id": str(dataset.id),
            "datasetCode": dataset.dataset_code,
            "datasetVersion": dataset.dataset_version,
            "contentChecksum": dataset.content_checksum,
            "sourceWorkbookName": dataset.source_workbook_name,
            "sourceWorkbookSha256": dataset.source_workbook_sha256,
            "sourceTemplateVersion": dataset.source_template_version,
            "regulationReference": dataset.regulation_reference,
            "validFrom": dataset.valid_from.isoformat(),
            "validUntil": dataset.valid_until.isoformat() if dataset.valid_until else None,
        },
        "value": {
            "id": str(value.id),
            "countryName": value.country_name,
            "isOtherCountriesGroup": value.is_other_countries_group,
            "cnNormalizedCode": value.cn_normalized_code,
            "cnDisplayCode": value.cn_display_code,
            "goodsCategory": value.goods_category,
            "goodsDescription": value.goods_description,
            "productionRoute": value.production_route,
            "directValue": _decimal_str(value.direct_value),
            "directValueStatus": value.direct_value_status,
            "indirectValue": _decimal_str(value.indirect_value),
            "indirectValueStatus": value.indirect_value_status,
            "totalValue": _decimal_str(value.total_value),
            "totalValueStatus": value.total_value_status,
            "markedUpTotals": dict(value.marked_up_totals_json or {}),
            "sourceSheet": value.source_sheet,
            "sourceRow": value.source_row,
            "lookupKey": value.lookup_key,
            "originalKeys": dict(value.original_keys_json or {}),
        },
        "units": {
            "specificDirect": value.direct_unit or SPECIFIC_DIRECT_UNIT,
            "specificIndirect": value.indirect_unit or SPECIFIC_INDIRECT_UNIT,
            "unitNote": value.unit_note,
        },
        "requestedKeys": {
            "countryOfOrigin": requested_country,
            "cnNormalizedCode": requested_cn,
            "productionRoute": requested_route,
            "goodsDescription": requested_description,
            "lookupKey": lookup_key,
        },
    }


def snapshot_specific_values(
    snapshot: dict[str, Any] | None,
) -> tuple[Decimal | None, Decimal | None]:
    """Numeric specific direct/indirect values from a stored snapshot (never live data)."""
    if not snapshot:
        return None, None
    value = snapshot.get("value")
    if not isinstance(value, dict):
        return None, None
    direct: Decimal | None = None
    indirect: Decimal | None = None
    if value.get("directValueStatus") == DV_STATUS_NUMERIC and value.get("directValue") is not None:
        direct = Decimal(str(value["directValue"]))
    if (
        value.get("indirectValueStatus") == DV_STATUS_NUMERIC
        and value.get("indirectValue") is not None
    ):
        indirect = Decimal(str(value["indirectValue"]))
    return direct, indirect
