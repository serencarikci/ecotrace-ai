"""Pure Decimal math for the Phase 10C product embedded-emissions roll-up.

Never uses float. Every identity below holds exactly on the raw (unquantized)
Decimal values; quantization is applied only to the reporting-scale mirrors.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class OwnProcessEmissions:
    """Absolute own-process emissions of one product (tCO2e numeric, GWP=1)."""

    dea_direct_tco2: Decimal
    heat_attributed_tco2e: Decimal
    waste_gas_attributed_tco2e: Decimal
    exported_electricity_direct_tco2e: Decimal
    own_direct_tco2e: Decimal
    own_indirect_tco2e: Decimal


def compute_own_process_emissions(
    *,
    dea_direct_tco2: Decimal,
    heat_attributed_tco2e: Decimal | None,
    waste_gas_attributed_tco2e: Decimal | None,
    iea_indirect_tco2e: Decimal,
    exported_electricity_direct_tco2e: Decimal = ZERO,
) -> OwnProcessEmissions:
    """Workbook D_Processes T54 + T58 + T62 + T72 (direct) and T66 (indirect).

    ``exported_electricity_direct_tco2e`` is always 0 in V1: the process block does
    not model L71/L72 and facility-level export must not be attributed to a product.
    """
    heat = heat_attributed_tco2e if heat_attributed_tco2e is not None else ZERO
    waste = waste_gas_attributed_tco2e if waste_gas_attributed_tco2e is not None else ZERO
    own_direct = dea_direct_tco2 + heat + waste + exported_electricity_direct_tco2e
    return OwnProcessEmissions(
        dea_direct_tco2=dea_direct_tco2,
        heat_attributed_tco2e=heat,
        waste_gas_attributed_tco2e=waste,
        exported_electricity_direct_tco2e=exported_electricity_direct_tco2e,
        own_direct_tco2e=own_direct,
        own_indirect_tco2e=iea_indirect_tco2e,
    )


@dataclass(frozen=True, slots=True)
class PrecursorContribution:
    """One (precursor, product-use) contribution to a single product."""

    precursor_id: uuid.UUID
    product_use_id: uuid.UUID
    quantity_tonnes: Decimal
    specific_direct: Decimal
    specific_indirect: Decimal
    contribution_direct_tco2e: Decimal
    contribution_indirect_tco2e: Decimal


def compute_precursor_contribution(
    *,
    precursor_id: uuid.UUID,
    product_use_id: uuid.UUID,
    quantity_tonnes: Decimal,
    specific_direct: Decimal,
    specific_indirect: Decimal,
) -> PrecursorContribution:
    """Reduced Leontief term: product-use quantity × precursor specific values.

    The workbook process-process block is zero in EcoTrace (no process-as-precursor),
    so the full matrix inverse collapses into this direct product.
    """
    if quantity_tonnes < 0:
        raise ValueError("PRECURSOR_USE_QUANTITY_NEGATIVE")
    return PrecursorContribution(
        precursor_id=precursor_id,
        product_use_id=product_use_id,
        quantity_tonnes=quantity_tonnes,
        specific_direct=specific_direct,
        specific_indirect=specific_indirect,
        contribution_direct_tco2e=quantity_tonnes * specific_direct,
        contribution_indirect_tco2e=quantity_tonnes * specific_indirect,
    )


@dataclass(frozen=True, slots=True)
class ProductTotals:
    own_direct_tco2e: Decimal
    own_indirect_tco2e: Decimal
    precursor_direct_tco2e: Decimal
    precursor_indirect_tco2e: Decimal
    total_direct_tco2e: Decimal
    total_indirect_tco2e: Decimal
    total_embedded_tco2e: Decimal


def compute_product_totals(
    *,
    own: OwnProcessEmissions,
    contributions: list[PrecursorContribution],
) -> ProductTotals:
    precursor_direct = sum((c.contribution_direct_tco2e for c in contributions), ZERO)
    precursor_indirect = sum((c.contribution_indirect_tco2e for c in contributions), ZERO)
    total_direct = own.own_direct_tco2e + precursor_direct
    total_indirect = own.own_indirect_tco2e + precursor_indirect
    return ProductTotals(
        own_direct_tco2e=own.own_direct_tco2e,
        own_indirect_tco2e=own.own_indirect_tco2e,
        precursor_direct_tco2e=precursor_direct,
        precursor_indirect_tco2e=precursor_indirect,
        total_direct_tco2e=total_direct,
        total_indirect_tco2e=total_indirect,
        total_embedded_tco2e=total_direct + total_indirect,
    )


@dataclass(frozen=True, slots=True)
class ProductSpecifics:
    denominator_tonnes: Decimal
    specific_direct: Decimal
    specific_indirect: Decimal
    specific_total: Decimal


def compute_product_specifics(
    *,
    totals: ProductTotals,
    denominator_tonnes: Decimal,
) -> ProductSpecifics:
    """Specific embedded emissions per tonne of produced goods (fail closed on 0)."""
    if denominator_tonnes <= 0:
        raise ValueError("PRODUCT_DENOMINATOR_ZERO")
    return ProductSpecifics(
        denominator_tonnes=denominator_tonnes,
        specific_direct=totals.total_direct_tco2e / denominator_tonnes,
        specific_indirect=totals.total_indirect_tco2e / denominator_tonnes,
        specific_total=totals.total_embedded_tco2e / denominator_tonnes,
    )


def assert_product_identities(
    *,
    totals: ProductTotals,
    specifics: ProductSpecifics | None = None,
) -> None:
    """Exact Decimal identity guard used by the engine before persistence."""
    if totals.total_direct_tco2e != totals.own_direct_tco2e + totals.precursor_direct_tco2e:
        raise ValueError("DIRECT_TOTAL_IDENTITY_BROKEN")
    if totals.total_indirect_tco2e != totals.own_indirect_tco2e + totals.precursor_indirect_tco2e:
        raise ValueError("INDIRECT_TOTAL_IDENTITY_BROKEN")
    if totals.total_embedded_tco2e != totals.total_direct_tco2e + totals.total_indirect_tco2e:
        raise ValueError("EMBEDDED_TOTAL_IDENTITY_BROKEN")
    if specifics is None:
        return
    if specifics.denominator_tonnes <= 0:
        raise ValueError("PRODUCT_DENOMINATOR_ZERO")


@dataclass(frozen=True, slots=True)
class BindingTotals:
    total_direct_tco2e: Decimal
    total_indirect_tco2e: Decimal
    total_embedded_tco2e: Decimal


def aggregate_binding_totals(rows: list[ProductTotals]) -> BindingTotals:
    direct = sum((r.total_direct_tco2e for r in rows), ZERO)
    indirect = sum((r.total_indirect_tco2e for r in rows), ZERO)
    return BindingTotals(
        total_direct_tco2e=direct,
        total_indirect_tco2e=indirect,
        total_embedded_tco2e=direct + indirect,
    )


def golden_single_precursor_product(
    *,
    produced_tonnes: Decimal = Decimal("10"),
    dea_direct_tco2: Decimal = Decimal("1"),
    iea_indirect_tco2e: Decimal = Decimal("2"),
    precursor_use_tonnes: Decimal = Decimal("3"),
    precursor_specific_direct: Decimal = Decimal("0.5"),
    precursor_specific_indirect: Decimal = Decimal("0.1"),
) -> tuple[ProductTotals, ProductSpecifics]:
    """Synthetic golden fixture (one product, one purchased precursor, no heat/waste)."""
    own = compute_own_process_emissions(
        dea_direct_tco2=dea_direct_tco2,
        heat_attributed_tco2e=ZERO,
        waste_gas_attributed_tco2e=ZERO,
        iea_indirect_tco2e=iea_indirect_tco2e,
    )
    contribution = compute_precursor_contribution(
        precursor_id=uuid.UUID(int=1),
        product_use_id=uuid.UUID(int=2),
        quantity_tonnes=precursor_use_tonnes,
        specific_direct=precursor_specific_direct,
        specific_indirect=precursor_specific_indirect,
    )
    totals = compute_product_totals(own=own, contributions=[contribution])
    specifics = compute_product_specifics(totals=totals, denominator_tonnes=produced_tonnes)
    assert_product_identities(totals=totals, specifics=specifics)
    return totals, specifics
