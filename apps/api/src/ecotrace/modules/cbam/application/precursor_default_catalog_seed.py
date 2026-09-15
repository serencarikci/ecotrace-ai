"""Idempotent seed for the EU precursor default-value catalog (Phase 10A)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from decimal import Decimal
from importlib import resources
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import ConflictError
from ecotrace.modules.cbam.application.precursor_constants import (
    DEFAULT_DATASET_STATUS_ACTIVE,
    LOOKUP_KEY_MAX_LENGTH,
    LOOKUP_KEY_SEPARATOR,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamPrecursorDefaultDataset,
    CbamPrecursorDefaultValue,
)

SEED_PACKAGE = "ecotrace.modules.cbam.data"
SEED_FILENAME = "cbam_precursor_defaults_v20260204.json"
INSERT_CHUNK_SIZE = 500


def load_precursor_default_seed_payload() -> dict[str, Any]:
    try:
        root = resources.files(SEED_PACKAGE)
        raw = (root / SEED_FILENAME).read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError, AttributeError, ModuleNotFoundError):
        path = Path(__file__).resolve().parent.parent / "data" / SEED_FILENAME
        raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("Precursor default-value seed payload must be a JSON object")
    return data


def compute_seed_content_checksum(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload))
    clone.get("dataset", {}).pop("contentChecksum", None)
    canonical = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def normalize_lookup_segment(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.replace("\xa0", " ").split()).casefold()


def build_lookup_key(
    *,
    country_name: str | None,
    cn_normalized_code: str | None,
    production_route: str | None,
    goods_description: str | None,
) -> str:
    """`country|cn|route|description` with empty segments for absent parts."""
    key = LOOKUP_KEY_SEPARATOR.join(
        (
            normalize_lookup_segment(country_name),
            normalize_lookup_segment(cn_normalized_code),
            normalize_lookup_segment(production_route),
            normalize_lookup_segment(goods_description),
        )
    )
    return key[:LOOKUP_KEY_MAX_LENGTH]


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _value_rows(dataset_id: uuid.UUID, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload["values"]:
        rows.append(
            {
                "id": uuid.uuid4(),
                "dataset_id": dataset_id,
                "country_name": item["countryName"],
                "source_sheet": item["sourceSheet"],
                "source_row": int(item["sourceRow"]),
                "is_other_countries_group": bool(item.get("isOtherCountriesGroup", False)),
                "cn_normalized_code": item["cnNormalizedCode"],
                "cn_display_code": item.get("cnDisplayCode"),
                "goods_category": item.get("goodsCategory"),
                "goods_description": item.get("goodsDescription"),
                "production_route": item.get("productionRoute"),
                "direct_value": _decimal_or_none(item.get("directValue")),
                "direct_value_status": item["directValueStatus"],
                "indirect_value": _decimal_or_none(item.get("indirectValue")),
                "indirect_value_status": item["indirectValueStatus"],
                "total_value": _decimal_or_none(item.get("totalValue")),
                "total_value_status": item["totalValueStatus"],
                "direct_unit": item.get("directUnit"),
                "indirect_unit": item.get("indirectUnit"),
                "total_unit": item.get("totalUnit"),
                "unit_note": item.get("unitNote"),
                "marked_up_totals_json": item.get("markedUpTotals") or {},
                "original_keys_json": item.get("originalKeys") or {},
                "lookup_key": build_lookup_key(
                    country_name=item["countryName"],
                    cn_normalized_code=item["cnNormalizedCode"],
                    production_route=item.get("productionRoute"),
                    goods_description=item.get("goodsDescription"),
                ),
            }
        )
    return rows


def ensure_platform_precursor_default_catalog(db: Session) -> CbamPrecursorDefaultDataset:
    payload = load_precursor_default_seed_payload()
    dataset_meta = payload["dataset"]
    expected_checksum = compute_seed_content_checksum(payload)
    stored_checksum = dataset_meta.get("contentChecksum")
    if stored_checksum and stored_checksum != expected_checksum:
        raise ConflictError(
            "Precursor default-value seed contentChecksum does not match canonical payload.",
            details=[{"code": "SEED_CHECKSUM_MISMATCH"}],
        )

    existing = db.execute(
        select(CbamPrecursorDefaultDataset).where(
            CbamPrecursorDefaultDataset.dataset_code == dataset_meta["datasetCode"],
            CbamPrecursorDefaultDataset.dataset_version == dataset_meta["datasetVersion"],
        )
    ).scalar_one_or_none()

    if existing is not None:
        _assert_dataset_immutable(db, existing, dataset_meta, expected_checksum, payload)
        return existing

    dataset = CbamPrecursorDefaultDataset(
        id=uuid.uuid4(),
        dataset_code=dataset_meta["datasetCode"],
        dataset_version=dataset_meta["datasetVersion"],
        content_checksum=expected_checksum,
        source_workbook_name=dataset_meta["sourceWorkbookName"],
        source_workbook_sha256=dataset_meta["sourceWorkbookSha256"],
        source_template_version=dataset_meta["sourceTemplateVersion"],
        regulation_reference=dataset_meta.get("regulationReference"),
        valid_from=date.fromisoformat(dataset_meta["validFrom"]),
        valid_until=(
            date.fromisoformat(dataset_meta["validUntil"])
            if dataset_meta.get("validUntil")
            else None
        ),
        status=DEFAULT_DATASET_STATUS_ACTIVE,
        value_count=len(payload["values"]),
    )
    db.add(dataset)
    db.flush()

    rows = _value_rows(dataset.id, payload)
    for start in range(0, len(rows), INSERT_CHUNK_SIZE):
        chunk = rows[start : start + INSERT_CHUNK_SIZE]
        if chunk:
            db.execute(insert(CbamPrecursorDefaultValue), chunk)
        db.flush()
    return dataset


def _assert_dataset_immutable(
    db: Session,
    existing: CbamPrecursorDefaultDataset,
    dataset_meta: dict[str, Any],
    expected_checksum: str,
    payload: dict[str, Any],
) -> None:
    mismatches: list[dict[str, str]] = []
    expected_fields = {
        "content_checksum": expected_checksum,
        "source_workbook_sha256": dataset_meta["sourceWorkbookSha256"],
        "source_template_version": dataset_meta["sourceTemplateVersion"],
        "dataset_code": dataset_meta["datasetCode"],
        "dataset_version": dataset_meta["datasetVersion"],
    }
    for field, expected in expected_fields.items():
        actual = getattr(existing, field)
        if str(actual) != str(expected):
            mismatches.append({"field": field, "expected": str(expected), "actual": str(actual)})
    expected_count = len(payload["values"])
    actual_count = db.execute(
        select(func.count())
        .select_from(CbamPrecursorDefaultValue)
        .where(CbamPrecursorDefaultValue.dataset_id == existing.id)
    ).scalar_one()
    if int(actual_count) != expected_count:
        mismatches.append(
            {
                "field": "default_value_count",
                "expected": str(expected_count),
                "actual": str(actual_count),
            }
        )
    if mismatches:
        raise ConflictError(
            "Published precursor default-value dataset conflicts with seed for the same version.",
            details=[{"code": "IMMUTABLE_PRECURSOR_DV_DATASET_CONFLICT", "mismatches": mismatches}],
        )
