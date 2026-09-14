from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import ValidationAppError

INTERNAL_TEMPLATE_CODE = "ECOTRACE_SKDM_INTERNAL"
INTERNAL_TEMPLATE_VERSION = "1.0.0"
INTERNAL_MAPPING_VERSION = "internal-mapping-v1"


def cbam_storage_root() -> Path:
    root = Path(get_settings().report_storage_path).resolve() / "cbam"
    root.mkdir(parents=True, exist_ok=True)
    return root


def template_storage_path(*, code: str, version: str) -> Path:
    safe_code = _safe_segment(code)
    safe_version = _safe_segment(version)
    path = cbam_storage_root() / "templates" / safe_code / safe_version / "template.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_run_dir(
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    export_run_id: uuid.UUID,
) -> Path:
    path = (
        cbam_storage_root()
        / "organizations"
        / str(organization_id)
        / "periods"
        / str(binding_id)
        / "exports"
        / str(export_run_id)
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_uri(path: Path) -> str:
    root = cbam_storage_root()
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(root)
    except ValueError as exc:
        raise ValidationAppError("Invalid CBAM storage path.") from exc
    return str(rel).replace("\\", "/")


def resolve_uri(storage_uri: str) -> Path:
    root = cbam_storage_root()
    candidate = (root / storage_uri).resolve()
    if not str(candidate).startswith(str(root)):
        raise ValidationAppError("Invalid CBAM storage path.")
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in value)
    if not cleaned or cleaned in {".", ".."}:
        raise ValidationAppError("Invalid storage path segment.")
    return cleaned
