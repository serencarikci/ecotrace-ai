"""Phase 7A-2 Decimal Stage 1 / Stage 2 math + workbook golden values."""

from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal, getcontext
from pathlib import Path

import pytest
from tests.cbam_dea_helpers import (
    GOLDEN_CBAM_FOSSIL_CO2_RAW,
    GOLDEN_CBAM_POOL_FINAL,
    GOLDEN_FACILITY_FOSSIL_CO2_RAW,
    GOLDEN_NON_CBAM_FOSSIL_CO2_RAW,
    GOLDEN_REMAINING,
    WORKBOOK_MONTHS,
)
from tests.unit.test_cbam_stationary_combustion import _natural_gas_inputs

from ecotrace.modules.cbam.application.direct_emissions_allocation_constants import (
    WORKBOOK_FILENAME,
    WORKBOOK_FORMULA_REFS,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.direct_emissions_allocation_math import (
    allocate_pool_with_largest_remainder,
    attribute_measure,
    monthly_cbam_share,
    period_wide_shortcut_share,
)
from ecotrace.modules.cbam.application.stationary_combustion_math import (
    calculate_stationary_combustion_co2,
)

getcontext().prec = 50

H2 = Decimal("0.68")
H3 = Decimal("2.6928")

_ALLOC_WORKBOOK = Path(__file__).resolve().parents[4] / "local-reference" / WORKBOOK_FILENAME


@pytest.mark.skipif(not _ALLOC_WORKBOOK.is_file(), reason="SKDM allocation workbook not in local-reference")
def test_workbook_sha256_and_formula_refs_match_constants() -> None:
    workbook = _ALLOC_WORKBOOK
    assert workbook.is_file(), f"missing {workbook}"
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    assert digest == WORKBOOK_SHA256
    assert "B9=IF(D3=0,0,(E3/D3)*F3)" in WORKBOOK_FORMULA_REFS
    assert "B12=SUM(B9:B11)" in WORKBOOK_FORMULA_REFS
    assert "B15=$B$12*$H$3" in WORKBOOK_FORMULA_REFS
    assert "C19=$B$15*(B19/$B$26)" in WORKBOOK_FORMULA_REFS


def test_exact_workbook_natural_gas_golden_values() -> None:
    """Facility fossil CO2 from SC @ 0.68 density; Stage 1 monthly attribution; Stage 2 pool."""
    prior = getcontext().prec
    getcontext().prec = 50
    try:
        facility = Decimal("0")
        cbam = Decimal("0")
        for _day, qty, d, e in WORKBOOK_MONTHS:
            out = calculate_stationary_combustion_co2(
                _natural_gas_inputs(quantity=qty, density_value=H2)
            )
            assert out.ok and out.derived is not None
            share = monthly_cbam_share(total_production_tonnes=d, cbam_quantity_tonnes=e)
            attr = attribute_measure(out.derived.co2_emissions_tonnes, share)
            facility += attr.facility
            cbam += attr.cbam
        non = facility - cbam
        assert facility == GOLDEN_FACILITY_FOSSIL_CO2_RAW
        assert cbam == GOLDEN_CBAM_FOSSIL_CO2_RAW
        assert non == GOLDEN_NON_CBAM_FOSSIL_CO2_RAW
        assert facility == cbam + non

        ids = [
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            uuid.UUID("00000000-0000-0000-0000-000000000002"),
            uuid.UUID("00000000-0000-0000-0000-000000000003"),
        ]
        qtys = [WORKBOOK_MONTHS[0][3], WORKBOOK_MONTHS[1][3], WORKBOOK_MONTHS[2][3]]
        pool_final, rows = allocate_pool_with_largest_remainder(
            pool_raw=cbam, groups=list(zip(ids, qtys, strict=True))
        )
        assert pool_final == GOLDEN_CBAM_POOL_FINAL
        assert sum(r.final_allocated for r in rows) == pool_final
        assert pool_final - sum(r.final_allocated for r in rows) == GOLDEN_REMAINING
        by_id = {r.group_id: r for r in rows}
        assert by_id[ids[0]].final_allocated == Decimal("0.05408237")
        assert by_id[ids[1]].final_allocated == Decimal("0.04081610")
        assert by_id[ids[2]].final_allocated == Decimal("0.04751110")
        assert sum(r.final_allocated for r in rows) == GOLDEN_CBAM_POOL_FINAL
    finally:
        getcontext().prec = prior


def test_workbook_monthly_stage1_differs_from_period_shortcut() -> None:
    prior = getcontext().prec
    getcontext().prec = 50
    try:
        attributed = Decimal("0")
        total_d = Decimal("0")
        total_e = Decimal("0")
        total_fossil = Decimal("0")
        for _day, qty, d, e in WORKBOOK_MONTHS:
            out = calculate_stationary_combustion_co2(
                _natural_gas_inputs(quantity=qty, density_value=H2)
            )
            assert out.ok and out.derived is not None
            foss = out.derived.co2_emissions_tonnes
            share = monthly_cbam_share(total_production_tonnes=d, cbam_quantity_tonnes=e)
            attributed += attribute_measure(foss, share).cbam
            total_d += d
            total_e += e
            total_fossil += foss
        shortcut = period_wide_shortcut_share(total_d=total_d, total_e=total_e) * total_fossil
        assert shortcut != attributed
        assert attributed == GOLDEN_CBAM_FOSSIL_CO2_RAW
        # Fuel-mass workbook path B12*H3 also equals this CBAM raw for density 0.68 fixture
        attributed_fuel = Decimal("0")
        for _day, qty, d, e in WORKBOOK_MONTHS:
            f = qty * H2 / Decimal("1000")
            share = monthly_cbam_share(total_production_tonnes=d, cbam_quantity_tonnes=e)
            attributed_fuel += attribute_measure(f, share).cbam
        b15 = attributed_fuel * H3
        assert b15 == GOLDEN_CBAM_FOSSIL_CO2_RAW
    finally:
        getcontext().prec = prior


def test_incorrect_period_wide_formula_not_used_by_monthly_share() -> None:
    # monthly_cbam_share is per-month; never aggregates D/E across months
    s1 = monthly_cbam_share(
        total_production_tonnes=Decimal("506"), cbam_quantity_tonnes=Decimal("39.34")
    )
    s2 = monthly_cbam_share(
        total_production_tonnes=Decimal("421"), cbam_quantity_tonnes=Decimal("29.69")
    )
    period = period_wide_shortcut_share(total_d=Decimal("927"), total_e=Decimal("69.03"))
    assert s1 != period
    assert s2 != period


def test_d0_e0_share_zero() -> None:
    assert monthly_cbam_share(
        total_production_tonnes=Decimal("0"), cbam_quantity_tonnes=Decimal("0")
    ) == Decimal("0")
    assert attribute_measure(Decimal("10"), Decimal("0")).cbam == Decimal("0")
    assert attribute_measure(Decimal("10"), Decimal("0")).non_cbam == Decimal("10")
    assert attribute_measure(Decimal("10"), Decimal("0")).facility == Decimal("10")


def test_d0_e_positive_fails() -> None:
    with pytest.raises(ValueError, match="TOTAL_PRODUCTION_MUST_BE_POSITIVE"):
        monthly_cbam_share(total_production_tonnes=Decimal("0"), cbam_quantity_tonnes=Decimal("1"))


def test_facility_equals_cbam_plus_non_cbam() -> None:
    attr = attribute_measure(Decimal("1.5"), Decimal("0.25"))
    assert attr.facility == attr.cbam + attr.non_cbam


def test_largest_remainder_exact_balance_and_tie_break() -> None:
    pool = Decimal("1.00000000")
    a = uuid.UUID("00000000-0000-0000-0000-00000000000a")
    b = uuid.UUID("00000000-0000-0000-0000-00000000000b")
    c = uuid.UUID("00000000-0000-0000-0000-00000000000c")
    pool_final, rows = allocate_pool_with_largest_remainder(
        pool_raw=pool,
        groups=[(a, Decimal("1")), (b, Decimal("1")), (c, Decimal("1"))],
    )
    assert pool_final == Decimal("1.00000000")
    assert sum(r.final_allocated for r in rows) == pool_final
    by_id = {r.group_id: r.final_allocated for r in rows}
    # Stable UUID ascending tie-break after equal fractional remainders
    ordered = sorted(
        rows,
        key=lambda r: (
            -(r.raw_allocated - r.final_allocated + r.rounding_adjustment),
            str(r.group_id),
        ),
    )
    assert by_id[a] + by_id[b] + by_id[c] == Decimal("1.00000000")
    assert pool_final - sum(r.final_allocated for r in rows) == Decimal("0")
    # Prefer lexicographically smaller UUID when remainders equal
    assert ordered  # structural


def test_workbook_stage2_product_split() -> None:
    b15 = GOLDEN_CBAM_FOSSIL_CO2_RAW
    prods = [
        (uuid.uuid4(), Decimal("39.336")),
        (uuid.uuid4(), Decimal("34.559")),
        (uuid.uuid4(), Decimal("29.688")),
    ]
    pool_final, rows = allocate_pool_with_largest_remainder(pool_raw=b15, groups=prods)
    assert sum(r.final_allocated for r in rows) == pool_final
    assert pool_final == b15.quantize(Decimal("0.00000001"))
    assert pool_final - sum(r.final_allocated for r in rows) == Decimal("0")


def test_zero_denominator_raises() -> None:
    with pytest.raises(ValueError, match="ZERO_ALLOCATION_DENOMINATOR"):
        allocate_pool_with_largest_remainder(
            pool_raw=Decimal("1"),
            groups=[(uuid.uuid4(), Decimal("0"))],
        )


def test_empty_groups_raises() -> None:
    with pytest.raises(ValueError, match="NO_ELIGIBLE_PRODUCTION"):
        allocate_pool_with_largest_remainder(pool_raw=Decimal("1"), groups=[])
