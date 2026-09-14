"""Exact-arithmetic Leontief solver tests (Phase 10D)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from ecotrace.modules.cbam.application.decimal_leontief import (
    CODE_SELF_REFERENCE,
    CODE_SINGULAR,
    InternalFlow,
    LeontiefError,
    build_system,
    order_profiles,
    solve_specific_embedded_emissions,
)

ZERO = Decimal("0")
ONE = Decimal("1")


def test_order_profiles_is_deterministic_by_uuid_string() -> None:
    a = uuid.UUID("00000000-0000-0000-0000-000000000002")
    b = uuid.UUID("00000000-0000-0000-0000-000000000001")
    assert order_profiles([a, b, a]) == (b, a)


def test_no_flows_yields_identity_system() -> None:
    first = uuid.UUID(int=1)
    second = uuid.UUID(int=2)
    system = build_system(
        profile_ids=[first, second],
        denominators={first: Decimal("10"), second: Decimal("20")},
        flows=[],
    )
    assert system.is_zero_matrix()
    assert system.identity_minus_a == ((ONE, ZERO), (ZERO, ONE))
    direct, indirect = solve_specific_embedded_emissions(
        system=system,
        base_direct=[Decimal("2"), Decimal("0.25")],
        base_indirect=[Decimal("0.4"), Decimal("0.05")],
    )
    assert direct == (Decimal("2"), Decimal("0.25"))
    assert indirect == (Decimal("0.4"), Decimal("0.05"))


def test_consumer_supplier_orientation() -> None:
    """A[consumer][supplier] = qty / TotProd(consumer)."""
    supplier = uuid.UUID(int=1)
    consumer = uuid.UUID(int=2)
    system = build_system(
        profile_ids=[supplier, consumer],
        denominators={supplier: Decimal("10"), consumer: Decimal("20")},
        flows=[
            InternalFlow(
                consumer_product_profile_version_id=consumer,
                supplier_product_profile_version_id=supplier,
                quantity_tonnes=Decimal("4"),
            )
        ],
    )
    # order is by UUID string → supplier(1) then consumer(2)
    assert system.order == (supplier, consumer)
    assert system.a_matrix[1][0] == Decimal("4") / Decimal("20")
    assert system.a_matrix[0][1] == ZERO


def test_self_reference_fails_closed() -> None:
    profile = uuid.UUID(int=1)
    with pytest.raises(LeontiefError) as exc:
        build_system(
            profile_ids=[profile],
            denominators={profile: Decimal("10")},
            flows=[
                InternalFlow(
                    consumer_product_profile_version_id=profile,
                    supplier_product_profile_version_id=profile,
                    quantity_tonnes=Decimal("1"),
                )
            ],
        )
    assert exc.value.code == CODE_SELF_REFERENCE


def test_singular_matrix_fails_closed() -> None:
    """A full self-consumption coefficient of 1 makes (I - A) singular."""
    first = uuid.UUID(int=1)
    second = uuid.UUID(int=2)
    system = build_system(
        profile_ids=[first, second],
        denominators={first: Decimal("10"), second: Decimal("10")},
        flows=[
            InternalFlow(
                consumer_product_profile_version_id=first,
                supplier_product_profile_version_id=second,
                quantity_tonnes=Decimal("10"),
            ),
            InternalFlow(
                consumer_product_profile_version_id=second,
                supplier_product_profile_version_id=first,
                quantity_tonnes=Decimal("10"),
            ),
        ],
    )
    with pytest.raises(LeontiefError) as exc:
        solve_specific_embedded_emissions(
            system=system,
            base_direct=[Decimal("1"), Decimal("1")],
            base_indirect=[Decimal("0"), Decimal("0")],
        )
    assert exc.value.code == CODE_SINGULAR
