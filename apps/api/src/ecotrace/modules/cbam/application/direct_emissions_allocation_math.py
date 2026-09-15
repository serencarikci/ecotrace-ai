"""Decimal Stage 1 / Stage 2 math for direct-emissions allocation (Phase 7A-2).

Never uses float. Never uses period-wide sum(E)/sum(D) as Stage 1.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from ecotrace.modules.cbam.application.calculation_math import RESULT_SCALE, quantize_result

ZERO = Decimal("0")


def monthly_cbam_share(
    *, total_production_tonnes: Decimal, cbam_quantity_tonnes: Decimal
) -> Decimal:
    """Workbook E/D share. D=0 and E=0 → 0; D=0 and E>0 is invalid."""
    if total_production_tonnes < 0 or cbam_quantity_tonnes < 0:
        raise ValueError("Quantities cannot be negative.")
    if total_production_tonnes > 0:
        return cbam_quantity_tonnes / total_production_tonnes
    if cbam_quantity_tonnes == 0:
        return ZERO
    raise ValueError("TOTAL_PRODUCTION_MUST_BE_POSITIVE")


@dataclass(frozen=True, slots=True)
class AttributedMeasures:
    facility: Decimal
    cbam: Decimal
    non_cbam: Decimal


def attribute_measure(facility: Decimal, share: Decimal) -> AttributedMeasures:
    cbam = facility * share
    non_cbam = facility - cbam
    return AttributedMeasures(facility=facility, cbam=cbam, non_cbam=non_cbam)


@dataclass(frozen=True, slots=True)
class ProductAllocationRow:
    group_id: uuid.UUID
    quantity: Decimal
    share: Decimal
    raw_allocated: Decimal
    final_allocated: Decimal
    rounding_adjustment: Decimal


def allocate_pool_with_largest_remainder(
    *,
    pool_raw: Decimal,
    groups: list[tuple[uuid.UUID, Decimal]],
) -> tuple[Decimal, list[ProductAllocationRow]]:
    """
    Stage 2 product split with exact conservation at RESULT_SCALE.

    groups: (stable_group_id, normalized_quantity_tonnes)
    Returns (pool_final, rows). Tie-break uses group_id string ascending.
    """
    if not groups:
        raise ValueError("NO_ELIGIBLE_PRODUCTION")
    denominator = sum((qty for _, qty in groups), ZERO)
    if denominator <= 0:
        raise ValueError("ZERO_ALLOCATION_DENOMINATOR")

    pool_final = quantize_result(pool_raw)
    provisional: list[tuple[uuid.UUID, Decimal, Decimal, Decimal, Decimal]] = []
    # (id, qty, share, exact, floored)
    for group_id, qty in groups:
        share = qty / denominator
        exact = pool_final * share
        floored = exact.quantize(RESULT_SCALE, rounding=ROUND_DOWN)
        provisional.append((group_id, qty, share, exact, floored))

    assigned = sum((row[4] for row in provisional), ZERO)
    remainder_units = int(
        ((pool_final - assigned) / RESULT_SCALE).to_integral_value(rounding=ROUND_HALF_UP)
    )

    # Rank by fractional part desc, then stable id asc.
    ranked = sorted(
        provisional,
        key=lambda r: (-(r[3] - r[4]), str(r[0])),
    )
    bump: dict[uuid.UUID, Decimal] = {r[0]: ZERO for r in provisional}
    for i in range(max(0, remainder_units)):
        bump[ranked[i % len(ranked)][0]] += RESULT_SCALE

    rows: list[ProductAllocationRow] = []
    for group_id, qty, share, exact, floored in provisional:
        final = floored + bump[group_id]
        rows.append(
            ProductAllocationRow(
                group_id=group_id,
                quantity=qty,
                share=share,
                raw_allocated=exact,
                final_allocated=final,
                rounding_adjustment=final - exact,
            )
        )

    total_final = sum((r.final_allocated for r in rows), ZERO)
    if total_final != pool_final:
        raise ValueError("UNBALANCED_ALLOCATION")
    return pool_final, rows


def period_wide_shortcut_share(
    *,
    total_d: Decimal,
    total_e: Decimal,
) -> Decimal:
    """Forbidden Stage-1 shortcut — exposed only for regression fixtures."""
    if total_d <= 0:
        return ZERO
    return total_e / total_d
