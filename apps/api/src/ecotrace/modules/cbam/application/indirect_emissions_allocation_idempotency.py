"""Idempotency fingerprint for indirect-emissions allocation executions."""

from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal

from ecotrace.modules.cbam.application.indirect_emissions_allocation_constants import (
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.stationary_combustion_idempotency import (
    canonicalize_decimal,
    canonicalize_optional_str,
)


def build_indirect_emissions_allocation_fingerprint(
    *,
    organization_id: uuid.UUID,
    binding_id: uuid.UUID,
    source_result_ids: list[uuid.UUID],
    source_material: list[tuple[uuid.UUID, Decimal, str, Decimal, str, Decimal]],
    monthly_basis: list[tuple[uuid.UUID, int, str, Decimal, Decimal, str]],
    production: list[tuple[uuid.UUID, Decimal, str, str, str]],
) -> str:
    """source_material: (result_id, activity_qty, unit, electricity_mwh, factor_mode, emissions)."""
    parts: list[str] = [
        str(organization_id),
        str(binding_id),
        METHODOLOGY_CODE,
        METHODOLOGY_VERSION,
        WORKBOOK_SHA256,
    ]
    for rid in sorted(source_result_ids, key=str):
        parts.append(f"src:{rid}")
    for rid, qty, unit, mwh, mode, em in sorted(source_material, key=lambda t: str(t[0])):
        parts.append(
            f"smat:{rid}|{canonicalize_decimal(qty)}|{canonicalize_optional_str(unit)}|"
            f"{canonicalize_decimal(mwh)}|{mode}|{canonicalize_decimal(em)}"
        )
    for bid, ver, month, d, e, unit in sorted(monthly_basis, key=lambda t: (t[2], str(t[0]))):
        parts.append(
            f"mb:{bid}|{ver}|{month}|"
            f"{canonicalize_decimal(d)}|{canonicalize_decimal(e)}|"
            f"{canonicalize_optional_str(unit)}"
        )
    for pid, qty, unit, pdate, profile in sorted(production, key=lambda t: str(t[0])):
        parts.append(
            f"pr:{pid}|{canonicalize_decimal(qty)}|"
            f"{canonicalize_optional_str(unit)}|{pdate}|{profile}"
        )
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
