"""Phase 10D V2 roll-up math: Leontief propagation + identity guards."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from ecotrace.modules.cbam.application.decimal_leontief import CODE_SINGULAR, LeontiefError
from ecotrace.modules.cbam.application.product_embedded_emissions_math import (
    ZERO,
    compute_own_process_emissions,
    compute_product_specifics,
    compute_product_totals,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_v2_math import (
    InternalFlowInput,
    ProductV2Input,
    compute_v2_rollup,
    golden_two_stage_internal_chain,
)


def test_no_flow_equals_v1_totals() -> None:
    profile = uuid.UUID(int=1)
    own = compute_own_process_emissions(
        dea_direct_tco2=Decimal('10'),
        heat_attributed_tco2e=Decimal('0'),
        waste_gas_attributed_tco2e=Decimal('0'),
        iea_indirect_tco2e=Decimal('2'),
        exported_electricity_direct_tco2e=ZERO,
    )
    v1_totals = compute_product_totals(own=own, contributions=[])
    v1_specifics = compute_product_specifics(
        totals=v1_totals, denominator_tonnes=Decimal('5')
    )
    rollup = compute_v2_rollup(
        products=[
            ProductV2Input(
                product_profile_version_id=profile,
                denominator_tonnes=Decimal('5'),
                own_direct_tco2e=own.own_direct_tco2e,
                own_indirect_tco2e=own.own_indirect_tco2e,
                purchased_direct_tco2e=ZERO,
                purchased_indirect_tco2e=ZERO,
            )
        ],
        flows=[],
    )
    result = rollup.results[profile]
    assert result.totals.total_direct_tco2e == v1_totals.total_direct_tco2e
    assert result.totals.total_indirect_tco2e == v1_totals.total_indirect_tco2e
    assert result.totals.total_embedded_tco2e == v1_totals.total_embedded_tco2e
    assert result.specifics.specific_total == v1_specifics.specific_total
    assert result.internal_contributions == ()


def test_one_to_two_internal_chain_golden() -> None:
    rollup = golden_two_stage_internal_chain()
    first = uuid.UUID(int=1)
    second = uuid.UUID(int=2)
    assert rollup.results[first].totals.internal_direct_tco2e == ZERO
    assert rollup.results[first].totals.total_direct_tco2e == Decimal('20')
    # Product 2 inherits 4 t × supplier SEE direct 2 tCO2e/t = 8
    assert rollup.results[second].totals.internal_direct_tco2e == Decimal('8')
    assert rollup.results[second].totals.total_direct_tco2e == Decimal('13')
    assert rollup.results[second].totals.internal_indirect_tco2e == Decimal('1.6')
    assert rollup.internal_contribution_count == 1


def test_three_stage_chain() -> None:
    p1, p2, p3 = uuid.UUID(int=1), uuid.UUID(int=2), uuid.UUID(int=3)
    rollup = compute_v2_rollup(
        products=[
            ProductV2Input(
                product_profile_version_id=p1,
                denominator_tonnes=Decimal('10'),
                own_direct_tco2e=Decimal('20'),
                own_indirect_tco2e=ZERO,
                purchased_direct_tco2e=ZERO,
                purchased_indirect_tco2e=ZERO,
            ),
            ProductV2Input(
                product_profile_version_id=p2,
                denominator_tonnes=Decimal('10'),
                own_direct_tco2e=Decimal('0'),
                own_indirect_tco2e=ZERO,
                purchased_direct_tco2e=ZERO,
                purchased_indirect_tco2e=ZERO,
            ),
            ProductV2Input(
                product_profile_version_id=p3,
                denominator_tonnes=Decimal('10'),
                own_direct_tco2e=Decimal('0'),
                own_indirect_tco2e=ZERO,
                purchased_direct_tco2e=ZERO,
                purchased_indirect_tco2e=ZERO,
            ),
        ],
        flows=[
            InternalFlowInput(
                product_use_id=uuid.UUID(int=11),
                consumer_product_profile_version_id=p2,
                supplier_product_profile_version_id=p1,
                quantity_tonnes=Decimal('5'),
            ),
            InternalFlowInput(
                product_use_id=uuid.UUID(int=12),
                consumer_product_profile_version_id=p3,
                supplier_product_profile_version_id=p2,
                quantity_tonnes=Decimal('5'),
            ),
        ],
    )
    # p1 SEE = 2; p2 inherits 5×2=10 → SEE=1; p3 inherits 5×1=5
    assert rollup.results[p2].totals.internal_direct_tco2e == Decimal('10')
    assert rollup.results[p3].totals.internal_direct_tco2e == Decimal('5')
    assert rollup.results[p3].specifics.specific_direct == Decimal('0.5')


def test_singular_internal_matrix_raises() -> None:
    a, b = uuid.UUID(int=1), uuid.UUID(int=2)
    with pytest.raises(LeontiefError) as exc:
        compute_v2_rollup(
            products=[
                ProductV2Input(
                    product_profile_version_id=a,
                    denominator_tonnes=Decimal('10'),
                    own_direct_tco2e=Decimal('1'),
                    own_indirect_tco2e=ZERO,
                    purchased_direct_tco2e=ZERO,
                    purchased_indirect_tco2e=ZERO,
                ),
                ProductV2Input(
                    product_profile_version_id=b,
                    denominator_tonnes=Decimal('10'),
                    own_direct_tco2e=Decimal('1'),
                    own_indirect_tco2e=ZERO,
                    purchased_direct_tco2e=ZERO,
                    purchased_indirect_tco2e=ZERO,
                ),
            ],
            flows=[
                InternalFlowInput(
                    product_use_id=uuid.UUID(int=3),
                    consumer_product_profile_version_id=a,
                    supplier_product_profile_version_id=b,
                    quantity_tonnes=Decimal('10'),
                ),
                InternalFlowInput(
                    product_use_id=uuid.UUID(int=4),
                    consumer_product_profile_version_id=b,
                    supplier_product_profile_version_id=a,
                    quantity_tonnes=Decimal('10'),
                ),
            ],
        )
    assert exc.value.code == CODE_SINGULAR
