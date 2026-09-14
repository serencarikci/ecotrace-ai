from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal


def canonicalize_decimal(value: Decimal | None) -> str:
    if value is None:
        return "-"
    # Fixed-point string; avoids float and unstable hash()/repr() forms.
    normalized = value.normalize() if value != 0 else Decimal("0")
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def canonicalize_optional_str(value: str | None) -> str:
    if value is None:
        return "-"
    stripped = value.strip()
    return stripped if stripped else "-"


def build_stationary_combustion_request_fingerprint(
    *,
    organization_id: uuid.UUID,
    reporting_period_binding_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    fuel_code: str,
    reference_date: date,
    density_value: Decimal | None,
    density_unit: str | None,
    dataset_version: str | None,
) -> str:
    parts = (
        str(organization_id),
        str(reporting_period_binding_id),
        str(activity_record_id),
        fuel_code.strip().upper(),
        reference_date.isoformat(),
        canonicalize_decimal(density_value),
        canonicalize_optional_str(density_unit),
        canonicalize_optional_str(dataset_version),
    )
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
