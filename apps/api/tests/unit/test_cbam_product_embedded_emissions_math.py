"""Phase 10C pure Decimal math for the product embedded-emissions roll-up."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from ecotrace.modules.cbam.application.product_embedded_emissions_constants import (
    EXPORTED_ELECTRICITY_NOTE_CODE,
    INTERNAL_PRECURSOR_NOTE_CODE,
    METHODOLOGY_CODE,
    METHODOLOGY_VERSION,
    RESULT_UNIT_TCO2E,
    SPECIFIC_UNIT_TCO2E_PER_T,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.product_embedded_emissions_math import (
    ZERO,
    aggregate_binding_totals,
    assert_product_identities,
    compute_own_process_emissions,
    compute_precursor_contribution,
    compute_product_specifics,
    compute_product_totals,
    golden_single_precursor_product,
)


def test_methodology_identity_is_frozen() -> None:
    assert METHODOLOGY_CODE == "CBAM_PRODUCT_EMBEDDED_EMISSIONS_V1"
    assert METHODOLOGY_VERSION == "1.0.0"
    assert WORKBOOK_SHA256 == ("83170fde547c418dcae7f6a32852555d6874e092769f387b263108a231b2dd64")
    assert RESULT_UNIT_TCO2E == "tCO2e"
    assert SPECIFIC_UNIT_TCO2E_PER_T == "tCO2e/t"
    assert EXPORTED_ELECTRICITY_NOTE_CODE == (
        "PROCESS_LEVEL_EXPORTED_ELECTRICITY_INPUTS_NOT_MODELED"
    )
    assert INTERNAL_PRECURSOR_NOTE_CODE == "INTERNAL_PROCESS_PRECURSOR_LEONTIEF_NOT_MODELED"


def test_synthetic_golden_single_product_single_precursor() -> None:
    """produced=10 t, DEA=1, IEA=2, precursor 3 t × (0.5 direct, 0.1 indirect)."""
    totals, specifics = golden_single_precursor_product()

    assert totals.own_direct_tco2e == Decimal("1")
    assert totals.precursor_direct_tco2e == Decimal("1.5")
    assert totals.total_direct_tco2e == Decimal("2.5")
    assert totals.own_indirect_tco2e == Decimal("2")
    assert totals.precursor_indirect_tco2e == Decimal("0.3")
    assert totals.total_indirect_tco2e == Decimal("2.3")
    assert totals.total_embedded_tco2e == Decimal("4.8")

    assert specifics.denominator_tonnes == Decimal("10")
    assert specifics.specific_direct == Decimal("0.25")
    assert specifics.specific_indirect == Decimal("0.23")
    assert specifics.specific_total == Decimal("0.48")


def test_own_direct_sums_t54_t58_t62_and_t72_is_zero_in_v1() -> None:
    own = compute_own_process_emissions(
        dea_direct_tco2=Decimal("4.25"),
        heat_attributed_tco2e=Decimal("1.5"),
        waste_gas_attributed_tco2e=Decimal("-0.75"),
        iea_indirect_tco2e=Decimal("9"),
    )
    assert own.own_direct_tco2e == Decimal("5")
    assert own.exported_electricity_direct_tco2e == ZERO
    # Exported electricity never touches indirect (workbook S72=EmbedEmDir_).
    assert own.own_indirect_tco2e == Decimal("9")


def test_missing_heat_and_waste_gas_are_treated_as_zero_not_null() -> None:
    own = compute_own_process_emissions(
        dea_direct_tco2=Decimal("3"),
        heat_attributed_tco2e=None,
        waste_gas_attributed_tco2e=None,
        iea_indirect_tco2e=Decimal("1"),
    )
    assert own.heat_attributed_tco2e == ZERO
    assert own.waste_gas_attributed_tco2e == ZERO
    assert own.own_direct_tco2e == Decimal("3")


def test_precursor_contribution_uses_product_use_quantity_not_total_purchased() -> None:
    contribution = compute_precursor_contribution(
        precursor_id=uuid.UUID(int=7),
        product_use_id=uuid.UUID(int=8),
        quantity_tonnes=Decimal("3"),
        specific_direct=Decimal("0.5"),
        specific_indirect=Decimal("0.1"),
    )
    assert contribution.contribution_direct_tco2e == Decimal("1.5")
    assert contribution.contribution_indirect_tco2e == Decimal("0.3")


def test_negative_product_use_quantity_is_rejected() -> None:
    with pytest.raises(ValueError, match="PRECURSOR_USE_QUANTITY_NEGATIVE"):
        compute_precursor_contribution(
            precursor_id=uuid.UUID(int=1),
            product_use_id=uuid.UUID(int=2),
            quantity_tonnes=Decimal("-1"),
            specific_direct=Decimal("0.5"),
            specific_indirect=Decimal("0.1"),
        )


def test_zero_denominator_fails_closed() -> None:
    own = compute_own_process_emissions(
        dea_direct_tco2=Decimal("1"),
        heat_attributed_tco2e=ZERO,
        waste_gas_attributed_tco2e=ZERO,
        iea_indirect_tco2e=Decimal("1"),
    )
    totals = compute_product_totals(own=own, contributions=[])
    for denominator in (Decimal("0"), Decimal("-5")):
        with pytest.raises(ValueError, match="PRODUCT_DENOMINATOR_ZERO"):
            compute_product_specifics(totals=totals, denominator_tonnes=denominator)


def test_identities_hold_exactly_on_repeating_decimals() -> None:
    own = compute_own_process_emissions(
        dea_direct_tco2=Decimal("1"),
        heat_attributed_tco2e=ZERO,
        waste_gas_attributed_tco2e=ZERO,
        iea_indirect_tco2e=Decimal("2"),
    )
    contributions = [
        compute_precursor_contribution(
            precursor_id=uuid.UUID(int=i),
            product_use_id=uuid.UUID(int=100 + i),
            quantity_tonnes=Decimal("0.333"),
            specific_direct=Decimal("1.7"),
            specific_indirect=Decimal("0.9"),
        )
        for i in range(1, 4)
    ]
    totals = compute_product_totals(own=own, contributions=contributions)
    specifics = compute_product_specifics(totals=totals, denominator_tonnes=Decimal("3"))
    assert_product_identities(totals=totals, specifics=specifics)
    assert totals.precursor_direct_tco2e == Decimal("0.999") * Decimal("1.7")
    assert totals.total_embedded_tco2e == (totals.total_direct_tco2e + totals.total_indirect_tco2e)


def test_binding_aggregate_is_the_sum_of_product_totals() -> None:
    rows = []
    for direct, indirect in ((Decimal("2.5"), Decimal("2.3")), (Decimal("1"), Decimal("4"))):
        own = compute_own_process_emissions(
            dea_direct_tco2=direct,
            heat_attributed_tco2e=ZERO,
            waste_gas_attributed_tco2e=ZERO,
            iea_indirect_tco2e=indirect,
        )
        rows.append(compute_product_totals(own=own, contributions=[]))
    aggregate = aggregate_binding_totals(rows)
    assert aggregate.total_direct_tco2e == Decimal("3.5")
    assert aggregate.total_indirect_tco2e == Decimal("6.3")
    assert aggregate.total_embedded_tco2e == Decimal("9.8")
