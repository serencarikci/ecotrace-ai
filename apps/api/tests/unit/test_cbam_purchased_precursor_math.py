"""Phase 10A purchased-precursor pure math (E_PurchPrec L39/L52/T49/T52)."""

from __future__ import annotations

from decimal import Decimal

from ecotrace.modules.cbam.application.precursor_constants import (
    BALANCE_BALANCED,
    BALANCE_INCOMPLETE,
    BALANCE_UNBALANCED,
    CALC_STATUS_CALCULATED,
    CALC_STATUS_INCOMPLETE,
)
from ecotrace.modules.cbam.application.precursor_math import (
    compute_precursor_distribution_balance,
    compute_specific_indirect,
    compute_total_embedded,
)


def test_balance_exact_zero_is_balanced() -> None:
    balance = compute_precursor_distribution_balance(
        purchased_tonnes=Decimal('10'),
        product_use_tonnes=Decimal('7.5'),
        non_cbam_tonnes=Decimal('2.5'),
    )
    assert balance.distributed_tonnes == Decimal('10')
    assert balance.remaining_tonnes == Decimal('0')
    assert balance.balance_status == BALANCE_BALANCED


def test_balance_has_no_rounding_tolerance() -> None:
    """L39 is compared exactly; a 1e-8 t residue is still UNBALANCED."""
    balance = compute_precursor_distribution_balance(
        purchased_tonnes=Decimal('10'),
        product_use_tonnes=Decimal('7.5'),
        non_cbam_tonnes=Decimal('2.49999999'),
    )
    assert balance.remaining_tonnes == Decimal('0.00000001')
    assert balance.balance_status == BALANCE_UNBALANCED


def test_balance_over_distribution_is_negative_remaining() -> None:
    balance = compute_precursor_distribution_balance(
        purchased_tonnes=Decimal('10'),
        product_use_tonnes=Decimal('9'),
        non_cbam_tonnes=Decimal('3'),
    )
    assert balance.remaining_tonnes == Decimal('-2')
    assert balance.balance_status == BALANCE_UNBALANCED


def test_balance_incomplete_when_quantity_or_non_cbam_missing() -> None:
    missing_purchased = compute_precursor_distribution_balance(
        purchased_tonnes=None,
        product_use_tonnes=Decimal('1'),
        non_cbam_tonnes=Decimal('0'),
    )
    assert missing_purchased.balance_status == BALANCE_INCOMPLETE
    assert missing_purchased.remaining_tonnes is None
    assert missing_purchased.distributed_tonnes is None

    missing_non_cbam = compute_precursor_distribution_balance(
        purchased_tonnes=Decimal('1'),
        product_use_tonnes=Decimal('1'),
        non_cbam_tonnes=None,
    )
    assert missing_non_cbam.balance_status == BALANCE_INCOMPLETE
    assert missing_non_cbam.remaining_tonnes is None


def test_specific_indirect_is_l50_times_l51() -> None:
    assert compute_specific_indirect(
        electricity_intensity=Decimal('2'),
        electricity_emission_factor=Decimal('0.3'),
    ) == Decimal('0.6')
    assert (
        compute_specific_indirect(
            electricity_intensity=None, electricity_emission_factor=Decimal('0.3')
        )
        is None
    )
    assert (
        compute_specific_indirect(
            electricity_intensity=Decimal('2'), electricity_emission_factor=None
        )
        is None
    )


def test_specific_indirect_keeps_full_decimal_precision() -> None:
    """Workbook L50/L51 for the SEE example: 0.3980732346658671 * 0.442."""
    assert compute_specific_indirect(
        electricity_intensity=Decimal('0.3980732346658671'),
        electricity_emission_factor=Decimal('0.442'),
    ) == Decimal('0.1759483697223132582')


def test_total_embedded_golden() -> None:
    """qty=10 t, L49=1.5, L50=2, L51=0.3 → L52=0.6, T49=15, T52=6, total=21."""
    specific_indirect = compute_specific_indirect(
        electricity_intensity=Decimal('2'),
        electricity_emission_factor=Decimal('0.3'),
    )
    assert specific_indirect == Decimal('0.6')

    totals = compute_total_embedded(
        quantity_tonnes=Decimal('10'),
        specific_direct=Decimal('1.5'),
        specific_indirect=specific_indirect,
    )
    assert totals.status == CALC_STATUS_CALCULATED
    assert totals.total_direct_tco2e == Decimal('15.0')
    assert totals.total_indirect_tco2e == Decimal('6.0')
    assert totals.total_tco2e == Decimal('21.0')


def test_total_embedded_incomplete_when_any_leg_missing() -> None:
    no_indirect = compute_total_embedded(
        quantity_tonnes=Decimal('10'),
        specific_direct=Decimal('1.5'),
        specific_indirect=None,
    )
    assert no_indirect.status == CALC_STATUS_INCOMPLETE
    assert no_indirect.total_direct_tco2e == Decimal('15.0')
    assert no_indirect.total_indirect_tco2e is None
    assert no_indirect.total_tco2e is None

    no_quantity = compute_total_embedded(
        quantity_tonnes=None,
        specific_direct=Decimal('1.5'),
        specific_indirect=Decimal('0.6'),
    )
    assert no_quantity.status == CALC_STATUS_INCOMPLETE
    assert no_quantity.total_tco2e is None


def test_total_embedded_zero_quantity_still_calculates() -> None:
    totals = compute_total_embedded(
        quantity_tonnes=Decimal('0'),
        specific_direct=Decimal('1.5'),
        specific_indirect=Decimal('0.6'),
    )
    assert totals.status == CALC_STATUS_CALCULATED
    assert totals.total_tco2e == Decimal('0.0')
