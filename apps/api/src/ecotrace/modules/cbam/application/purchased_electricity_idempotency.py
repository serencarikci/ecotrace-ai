"""Purchased-electricity execution fingerprint / idempotency helpers."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal

from ecotrace.modules.cbam.application.stationary_combustion_idempotency import (
    canonicalize_decimal,
    canonicalize_optional_str,
)


def build_purchased_electricity_request_fingerprint(
    *,
    organization_id: uuid.UUID,
    reporting_period_binding_id: uuid.UUID,
    activity_record_id: uuid.UUID,
    factor_source_mode: str,
    reference_date: date,
    activity_quantity: Decimal,
    activity_unit: str,
    factor_value: Decimal | None,
    factor_unit: str | None,
    factor_value_id: uuid.UUID | None,
    exported_quantity: Decimal | None,
    exported_unit: str | None,
    manual_source_name: str | None,
    manual_source_document: str | None,
    manual_dataset_version: str | None,
    manual_reference_description: str | None,
) -> str:
    parts = (
        str(organization_id),
        str(reporting_period_binding_id),
        str(activity_record_id),
        factor_source_mode.strip().upper(),
        reference_date.isoformat(),
        canonicalize_decimal(activity_quantity),
        activity_unit.strip(),
        canonicalize_decimal(factor_value),
        canonicalize_optional_str(factor_unit),
        str(factor_value_id) if factor_value_id is not None else "-",
        canonicalize_decimal(exported_quantity),
        canonicalize_optional_str(exported_unit),
        canonicalize_optional_str(manual_source_name),
        canonicalize_optional_str(manual_source_document),
        canonicalize_optional_str(manual_dataset_version),
        canonicalize_optional_str(manual_reference_description),
    )
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
