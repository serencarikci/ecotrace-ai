"""Math helpers — reuses Phase 7A-2 pure allocation primitives.

Electricity Stage 1 is monthly E/D on immutable PE electricity_mwh and
indirect_emissions_tco2e snapshots (never period-wide sum(E)/sum(D), never live factor).
"""

from __future__ import annotations

from decimal import Decimal

# Re-export shared pure helpers (single source of truth for share + largest-remainder).
from ecotrace.modules.cbam.application.direct_emissions_allocation_math import (
    ZERO,
    AttributedMeasures,
    ProductAllocationRow,
    allocate_pool_with_largest_remainder,
    attribute_measure,
    monthly_cbam_share,
    period_wide_shortcut_share,
)

__all__ = [
    "ZERO",
    "AttributedMeasures",
    "ProductAllocationRow",
    "allocate_pool_with_largest_remainder",
    "attribute_measure",
    "kwh_to_mwh",
    "monthly_cbam_share",
    "period_wide_shortcut_share",
]


def kwh_to_mwh(quantity_kwh: Decimal) -> Decimal:
    """Workbook B→C conversion: kWh / 1000 → MWh."""
    return quantity_kwh / Decimal("1000")
