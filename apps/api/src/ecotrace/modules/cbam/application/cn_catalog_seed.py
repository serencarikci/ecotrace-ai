"""Idempotent seed for the CBAM SEE CN-code catalog (Phase 6A)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import ConflictError
from ecotrace.modules.cbam.application.field_applicability import (
    normalize_field_applicability,
)
from ecotrace.modules.cbam.infrastructure.models import (
    CbamCnCode,
    CbamCnCodeDataset,
    CbamCnControlledListValue,
)

SEED_PACKAGE = "ecotrace.modules.cbam.data"
SEED_FILENAME = "cbam_see_v2_1_cn_catalog.json"


def load_cn_catalog_seed_payload() -> dict[str, Any]:
    try:
        root = resources.files(SEED_PACKAGE)
        raw = (root / SEED_FILENAME).read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError, AttributeError, ModuleNotFoundError):
        path = Path(__file__).resolve().parent.parent / "data" / SEED_FILENAME
        raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise TypeError("CN catalog seed payload must be a JSON object")
    return data


def compute_seed_content_checksum(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload))
    clone.get("dataset", {}).pop("contentChecksum", None)
    canonical = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def ensure_platform_cn_catalog(db: Session) -> CbamCnCodeDataset:
    payload = load_cn_catalog_seed_payload()
    dataset_meta = payload["dataset"]
    expected_checksum = compute_seed_content_checksum(payload)
    stored_checksum = dataset_meta.get("contentChecksum")
    if stored_checksum and stored_checksum != expected_checksum:
        raise ConflictError(
            "CN catalog seed contentChecksum does not match canonical payload.",
            details=[{"code": "SEED_CHECKSUM_MISMATCH"}],
        )

    existing = db.execute(
        select(CbamCnCodeDataset).where(
            CbamCnCodeDataset.dataset_code == dataset_meta["datasetCode"],
            CbamCnCodeDataset.dataset_version == dataset_meta["datasetVersion"],
        )
    ).scalar_one_or_none()

    if existing is not None:
        _assert_dataset_immutable(db, existing, dataset_meta, expected_checksum, payload)
        return existing

    dataset = CbamCnCodeDataset(
        id=uuid.uuid4(),
        dataset_code=dataset_meta["datasetCode"],
        dataset_version=dataset_meta["datasetVersion"],
        content_checksum=expected_checksum,
        source_workbook_name=dataset_meta["sourceWorkbookName"],
        source_workbook_sha256=dataset_meta["sourceWorkbookSha256"],
        source_template_version=dataset_meta["sourceTemplateVersion"],
        valid_from=date.fromisoformat(dataset_meta["validFrom"]),
        valid_until=(
            date.fromisoformat(dataset_meta["validUntil"])
            if dataset_meta.get("validUntil")
            else None
        ),
        status="ACTIVE",
    )
    db.add(dataset)
    db.flush()

    source_sheet = dataset_meta["sourceSheets"]["cnCodes"]
    for row in payload["cnCodes"]:
        db.add(
            CbamCnCode(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                cn_key=row["cnKey"],
                normalized_code=row["normalizedCode"],
                display_code=row["displayCode"],
                description_en=row["descriptionEn"],
                cbam_sector=row["cbamSector"],
                numbering_label=row.get("numberingLabel"),
                source_sheet=source_sheet,
                source_row=int(row["sourceRow"]),
                status="ACTIVE",
                field_applicability=normalize_field_applicability(row.get("fieldApplicability")),
            )
        )

    for list_code, values in payload.get("controlledLists", {}).items():
        for index, item in enumerate(values):
            db.add(
                CbamCnControlledListValue(
                    id=uuid.uuid4(),
                    dataset_id=dataset.id,
                    list_code=list_code,
                    value_code=item["code"],
                    value_label=item["label"],
                    sort_order=index,
                    status="ACTIVE",
                )
            )
    db.flush()
    return dataset


def _assert_dataset_immutable(
    db: Session,
    existing: CbamCnCodeDataset,
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
    expected_count = len(payload["cnCodes"])
    actual_count = db.execute(
        select(func.count()).select_from(CbamCnCode).where(CbamCnCode.dataset_id == existing.id)
    ).scalar_one()
    if int(actual_count) != expected_count:
        mismatches.append(
            {
                "field": "cn_code_count",
                "expected": str(expected_count),
                "actual": str(actual_count),
            }
        )
    if mismatches:
        raise ConflictError(
            "Published CN catalog dataset conflicts with seed for the same version.",
            details=[{"code": "IMMUTABLE_CN_DATASET_CONFLICT", "mismatches": mismatches}],
        )
