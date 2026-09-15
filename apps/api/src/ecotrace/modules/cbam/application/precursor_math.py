"""Purchased-precursor distribution balance and embedded-emission math (Phase 10A)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ecotrace.modules.cbam.application.precursor_constants import (
    BALANCE_BALANCED,
    BALANCE_INCOMPLETE,
    BALANCE_UNBALANCED,
    CALC_STATUS_CALCULATED,
    CALC_STATUS_INCOMPLETE,
)


@dataclass(frozen=True, slots=True)
class PrecursorDistributionBalance:
    purchased_tonnes: Decimal | None
    product_use_tonnes: Decimal
    non_cbam_tonnes: Decimal | None
    distributed_tonnes: Decimal | None
    remaining_tonnes: Decimal | None
    balance_status: str


def compute_precursor_distribution_balance(
    *,
    purchased_tonnes: Decimal | None,
    product_use_tonnes: Decimal,
    non_cbam_tonnes: Decimal | None,
) -> PrecursorDistributionBalance:
    """Exact Decimal balance (no business rounding tolerance).

    Workbook: E_PurchPrec!L39 = L25 - SUM(L28:L38)
    """
    if purchased_tonnes is None or non_cbam_tonnes is None:
        return PrecursorDistributionBalance(
            purchased_tonnes=purchased_tonnes,
            product_use_tonnes=product_use_tonnes,
            non_cbam_tonnes=non_cbam_tonnes,
            distributed_tonnes=None,
            remaining_tonnes=None,
            balance_status=BALANCE_INCOMPLETE,
        )

    distributed = product_use_tonnes + non_cbam_tonnes
    remaining = purchased_tonnes - distributed
    balanced = remaining == Decimal("0")
    return PrecursorDistributionBalance(
        purchased_tonnes=purchased_tonnes,
        product_use_tonnes=product_use_tonnes,
        non_cbam_tonnes=non_cbam_tonnes,
        distributed_tonnes=distributed,
        remaining_tonnes=remaining,
        balance_status=BALANCE_BALANCED if balanced else BALANCE_UNBALANCED,
    )


def compute_specific_indirect(
    *,
    electricity_intensity: Decimal | None,
    electricity_emission_factor: Decimal | None,
) -> Decimal | None:
    """Workbook L52 = L50*L51."""
    if electricity_intensity is None or electricity_emission_factor is None:
        return None
    return electricity_intensity * electricity_emission_factor


@dataclass(frozen=True, slots=True)
class TotalEmbeddedEmissions:
    status: str
    quantity_tonnes: Decimal | None
    specific_direct: Decimal | None
    specific_indirect: Decimal | None
    total_direct_tco2e: Decimal | None
    total_indirect_tco2e: Decimal | None
    total_tco2e: Decimal | None


def compute_total_embedded(
    *,
    quantity_tonnes: Decimal | None,
    specific_direct: Decimal | None,
    specific_indirect: Decimal | None,
) -> TotalEmbeddedEmissions:
    """Workbook T49 = L25*L49 and T52 = L25*L52."""
    total_direct: Decimal | None = None
    total_indirect: Decimal | None = None
    if quantity_tonnes is not None and specific_direct is not None:
        total_direct = quantity_tonnes * specific_direct
    if quantity_tonnes is not None and specific_indirect is not None:
        total_indirect = quantity_tonnes * specific_indirect

    total: Decimal | None = None
    if total_direct is not None and total_indirect is not None:
        total = total_direct + total_indirect

    status = CALC_STATUS_CALCULATED if total is not None else CALC_STATUS_INCOMPLETE
    return TotalEmbeddedEmissions(
        status=status,
        quantity_tonnes=quantity_tonnes,
        specific_direct=specific_direct,
        specific_indirect=specific_indirect,
        total_direct_tco2e=total_direct,
        total_indirect_tco2e=total_indirect,
        total_tco2e=total,
    )
