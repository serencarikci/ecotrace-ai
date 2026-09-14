"""(V2) product embedded-emissions math: internal Leontief propagation + T72.

Pure Decimal, no float anywhere. The reported figures are built so that every accounting
identity holds *exactly*:

* ``own + purchased + internal == total`` per product and per direction,
* ``internal == Σ internal contributions`` per product and per direction,
* ``purchased == Σ purchased-precursor contributions`` (unchanged from V1).

The Leontief solve supplies the supplier specific emissions used by each contribution;
the absolute totals are then reconstructed from those contributions rather than read back
from the solved vector, so persisted rows can never disagree with their own breakdown.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal, localcontext

from ecotrace.modules.cbam.application.decimal_leontief import (
    SOLVER_PRECISION,
    InternalFlow,
    LeontiefSystem,
    build_system,
    solve_specific_embedded_emissions,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_math import ZERO

__all__ = [
    'InternalContribution',
    'InternalFlowInput',
    'LeontiefRollup',
    'ProductV2Input',
    'ProductV2Result',
    'ProductV2Specifics',
    'ProductV2Totals',
    'assert_v2_product_identities',
    'compute_v2_rollup',
    'golden_two_stage_internal_chain',
]


@dataclass(frozen=True, slots=True)
class ProductV2Input:
    """Own and purchased absolute emissions of one product before internal propagation."""

    product_profile_version_id: uuid.UUID
    denominator_tonnes: Decimal
    own_direct_tco2e: Decimal
    own_indirect_tco2e: Decimal
    purchased_direct_tco2e: Decimal
    purchased_indirect_tco2e: Decimal


@dataclass(frozen=True, slots=True)
class InternalFlowInput:
    """One internal product-use edge: supplier output consumed by a consumer product."""

    product_use_id: uuid.UUID
    consumer_product_profile_version_id: uuid.UUID
    supplier_product_profile_version_id: uuid.UUID
    quantity_tonnes: Decimal


@dataclass(frozen=True, slots=True)
class InternalContribution:
    product_use_id: uuid.UUID
    consumer_product_profile_version_id: uuid.UUID
    supplier_product_profile_version_id: uuid.UUID
    quantity_tonnes: Decimal
    consumer_denominator_tonnes: Decimal
    a_coefficient: Decimal
    supplier_specific_direct: Decimal
    supplier_specific_indirect: Decimal
    contribution_direct_tco2e: Decimal
    contribution_indirect_tco2e: Decimal


@dataclass(frozen=True, slots=True)
class ProductV2Totals:
    own_direct_tco2e: Decimal
    own_indirect_tco2e: Decimal
    precursor_direct_tco2e: Decimal
    precursor_indirect_tco2e: Decimal
    internal_direct_tco2e: Decimal
    internal_indirect_tco2e: Decimal
    total_direct_tco2e: Decimal
    total_indirect_tco2e: Decimal
    total_embedded_tco2e: Decimal


@dataclass(frozen=True, slots=True)
class ProductV2Specifics:
    denominator_tonnes: Decimal
    specific_direct: Decimal
    specific_indirect: Decimal
    specific_total: Decimal


@dataclass(frozen=True, slots=True)
class ProductV2Result:
    product_profile_version_id: uuid.UUID
    base_specific_direct: Decimal
    base_specific_indirect: Decimal
    solver_specific_direct: Decimal
    solver_specific_indirect: Decimal
    totals: ProductV2Totals
    specifics: ProductV2Specifics
    internal_contributions: tuple[InternalContribution, ...]


@dataclass(frozen=True, slots=True)
class LeontiefRollup:
    system: LeontiefSystem
    results: dict[uuid.UUID, ProductV2Result]

    @property
    def internal_contribution_count(self) -> int:
        return sum(len(result.internal_contributions) for result in self.results.values())


def assert_v2_product_identities(
    *, totals: ProductV2Totals, contributions: tuple[InternalContribution, ...]
) -> None:
    """Exact Decimal guard run before anything is persisted."""
    if totals.total_direct_tco2e != (
        totals.own_direct_tco2e + totals.precursor_direct_tco2e + totals.internal_direct_tco2e
    ):
        raise ValueError('DIRECT_TOTAL_IDENTITY_BROKEN')
    if totals.total_indirect_tco2e != (
        totals.own_indirect_tco2e
        + totals.precursor_indirect_tco2e
        + totals.internal_indirect_tco2e
    ):
        raise ValueError('INDIRECT_TOTAL_IDENTITY_BROKEN')
    if totals.total_embedded_tco2e != totals.total_direct_tco2e + totals.total_indirect_tco2e:
        raise ValueError('EMBEDDED_TOTAL_IDENTITY_BROKEN')
    direct = sum((c.contribution_direct_tco2e for c in contributions), ZERO)
    indirect = sum((c.contribution_indirect_tco2e for c in contributions), ZERO)
    if direct != totals.internal_direct_tco2e:
        raise ValueError('INTERNAL_DIRECT_CONTRIBUTION_IDENTITY_BROKEN')
    if indirect != totals.internal_indirect_tco2e:
        raise ValueError('INTERNAL_INDIRECT_CONTRIBUTION_IDENTITY_BROKEN')


def compute_v2_rollup(
    *,
    products: list[ProductV2Input],
    flows: list[InternalFlowInput],
) -> LeontiefRollup:
    """Build ``A``, solve ``(I - A) · SEE = base`` and reconstruct exact product totals.

    Raises :class:`~ecotrace.modules.cbam.application.decimal_leontief.LeontiefError` when
    the matrix cannot be built or is singular; the caller turns that into a blocking code.
    """
    denominators = {p.product_profile_version_id: p.denominator_tonnes for p in products}
    for product in products:
        if product.denominator_tonnes <= ZERO:
            raise ValueError('PRODUCT_DENOMINATOR_ZERO')

    system = build_system(
        profile_ids=[p.product_profile_version_id for p in products],
        denominators=denominators,
        flows=[
            InternalFlow(
                consumer_product_profile_version_id=flow.consumer_product_profile_version_id,
                supplier_product_profile_version_id=flow.supplier_product_profile_version_id,
                quantity_tonnes=flow.quantity_tonnes,
            )
            for flow in flows
        ],
    )

    by_profile = {p.product_profile_version_id: p for p in products}
    with localcontext() as ctx:
        ctx.prec = SOLVER_PRECISION
        base_direct = [
            (
                by_profile[profile_id].own_direct_tco2e
                + by_profile[profile_id].purchased_direct_tco2e
            )
            / by_profile[profile_id].denominator_tonnes
            for profile_id in system.order
        ]
        base_indirect = [
            (
                by_profile[profile_id].own_indirect_tco2e
                + by_profile[profile_id].purchased_indirect_tco2e
            )
            / by_profile[profile_id].denominator_tonnes
            for profile_id in system.order
        ]

    solved_direct, solved_indirect = solve_specific_embedded_emissions(
        system=system,
        base_direct=base_direct,
        base_indirect=base_indirect,
    )

    flows_by_consumer: dict[uuid.UUID, list[InternalFlowInput]] = {}
    for flow in sorted(flows, key=lambda item: str(item.product_use_id)):
        flows_by_consumer.setdefault(flow.consumer_product_profile_version_id, []).append(flow)

    results: dict[uuid.UUID, ProductV2Result] = {}
    for position, profile_id in enumerate(system.order):
        product = by_profile[profile_id]
        contributions: list[InternalContribution] = []
        for flow in flows_by_consumer.get(profile_id, []):
            supplier_index = system.index[flow.supplier_product_profile_version_id]
            supplier_direct = solved_direct[supplier_index]
            supplier_indirect = solved_indirect[supplier_index]
            contributions.append(
                InternalContribution(
                    product_use_id=flow.product_use_id,
                    consumer_product_profile_version_id=profile_id,
                    supplier_product_profile_version_id=(
                        flow.supplier_product_profile_version_id
                    ),
                    quantity_tonnes=flow.quantity_tonnes,
                    consumer_denominator_tonnes=product.denominator_tonnes,
                    a_coefficient=system.a_matrix[position][supplier_index],
                    supplier_specific_direct=supplier_direct,
                    supplier_specific_indirect=supplier_indirect,
                    contribution_direct_tco2e=flow.quantity_tonnes * supplier_direct,
                    contribution_indirect_tco2e=flow.quantity_tonnes * supplier_indirect,
                )
            )

        internal_direct = sum((c.contribution_direct_tco2e for c in contributions), ZERO)
        internal_indirect = sum((c.contribution_indirect_tco2e for c in contributions), ZERO)
        total_direct = (
            product.own_direct_tco2e + product.purchased_direct_tco2e + internal_direct
        )
        total_indirect = (
            product.own_indirect_tco2e + product.purchased_indirect_tco2e + internal_indirect
        )
        totals = ProductV2Totals(
            own_direct_tco2e=product.own_direct_tco2e,
            own_indirect_tco2e=product.own_indirect_tco2e,
            precursor_direct_tco2e=product.purchased_direct_tco2e,
            precursor_indirect_tco2e=product.purchased_indirect_tco2e,
            internal_direct_tco2e=internal_direct,
            internal_indirect_tco2e=internal_indirect,
            total_direct_tco2e=total_direct,
            total_indirect_tco2e=total_indirect,
            total_embedded_tco2e=total_direct + total_indirect,
        )
        specifics = ProductV2Specifics(
            denominator_tonnes=product.denominator_tonnes,
            specific_direct=total_direct / product.denominator_tonnes,
            specific_indirect=total_indirect / product.denominator_tonnes,
            specific_total=totals.total_embedded_tco2e / product.denominator_tonnes,
        )
        frozen_contributions = tuple(contributions)
        assert_v2_product_identities(totals=totals, contributions=frozen_contributions)
        results[profile_id] = ProductV2Result(
            product_profile_version_id=profile_id,
            base_specific_direct=base_direct[position],
            base_specific_indirect=base_indirect[position],
            solver_specific_direct=solved_direct[position],
            solver_specific_indirect=solved_indirect[position],
            totals=totals,
            specifics=specifics,
            internal_contributions=frozen_contributions,
        )

    return LeontiefRollup(system=system, results=results)


def golden_two_stage_internal_chain() -> LeontiefRollup:
    """Synthetic golden fixture: product 1 supplies product 2 (no purchased precursors).

    Product 1 produces 10 t with 20 tCO2e own direct; 4 t of it feed product 2, which
    produces 20 t with 5 tCO2e own direct. Product 2 therefore inherits 4 × 2 = 8 tCO2e.
    """
    first = uuid.UUID(int=1)
    second = uuid.UUID(int=2)
    return compute_v2_rollup(
        products=[
            ProductV2Input(
                product_profile_version_id=first,
                denominator_tonnes=Decimal('10'),
                own_direct_tco2e=Decimal('20'),
                own_indirect_tco2e=Decimal('4'),
                purchased_direct_tco2e=ZERO,
                purchased_indirect_tco2e=ZERO,
            ),
            ProductV2Input(
                product_profile_version_id=second,
                denominator_tonnes=Decimal('20'),
                own_direct_tco2e=Decimal('5'),
                own_indirect_tco2e=Decimal('1'),
                purchased_direct_tco2e=ZERO,
                purchased_indirect_tco2e=ZERO,
            ),
        ],
        flows=[
            InternalFlowInput(
                product_use_id=uuid.UUID(int=3),
                consumer_product_profile_version_id=second,
                supplier_product_profile_version_id=first,
                quantity_tonnes=Decimal('4'),
            )
        ],
    )
