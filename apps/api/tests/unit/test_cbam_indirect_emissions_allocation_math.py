"""Phase 8C Decimal Stage 1 / Stage 2 math + workbook electricity goldens."""

from __future__ import annotations

import hashlib
import uuid
from decimal import Decimal, getcontext
from pathlib import Path

import pytest
from tests.cbam_iea_helpers import (
    GOLDEN_CBAM_EM_FINAL,
    GOLDEN_CBAM_EM_RAW,
    GOLDEN_CBAM_MWH_FINAL,
    GOLDEN_CBAM_MWH_RAW,
    GOLDEN_FACILITY_EM_RAW,
    GOLDEN_FACILITY_MWH_RAW,
    GOLDEN_REMAINING,
    H4,
    WORKBOOK_ELEC_MONTHS,
    WORKBOOK_PRODUCT_ELEC_FINALS,
    WORKBOOK_PRODUCT_EM_FINALS,
    WORKBOOK_PRODUCT_TONNES,
)

from ecotrace.modules.cbam.application.indirect_emissions_allocation_constants import (
    METHODOLOGY_CODE,
    WORKBOOK_FILENAME,
    WORKBOOK_FORMULA_REFS,
    WORKBOOK_SHA256,
)
from ecotrace.modules.cbam.application.indirect_emissions_allocation_math import (
    allocate_pool_with_largest_remainder,
    attribute_measure,
    kwh_to_mwh,
    monthly_cbam_share,
    period_wide_shortcut_share,
)
from ecotrace.modules.cbam.application.purchased_electricity_math import (
    calculate_indirect_electricity_emissions,
    to_mwh,
)

getcontext().prec = 50


def test_workbook_sha256_and_electricity_formula_refs() -> None:
    root = Path(__file__).resolve().parents[4]
    workbook = root / "local-reference" / WORKBOOK_FILENAME
    assert workbook.is_file(), f"missing {workbook}"
    digest = hashlib.sha256(workbook.read_bytes()).hexdigest()
    assert digest == WORKBOOK_SHA256
    assert "C9=IF(D3=0,0,(E3/D3)*(B3/1000))" in WORKBOOK_FORMULA_REFS
    assert "E9=D9*C9" in WORKBOOK_FORMULA_REFS
    assert "C12=SUM(C9:C11)" in WORKBOOK_FORMULA_REFS
    assert "B16=$C$12" in WORKBOOK_FORMULA_REFS
    assert "D19=$B$16*(B19/$B$26)" in WORKBOOK_FORMULA_REFS
    assert METHODOLOGY_CODE == "PURCHASED_ELECTRICITY_INDIRECT_EMISSIONS_ALLOCATION_V1"


def test_exact_workbook_electricity_stage1_and_b19_stage2() -> None:
    """Golden Stage 1 from monthly E/D; Stage 2 from workbook B19 product tonnes."""
    prior = getcontext().prec
    getcontext().prec = 50
    try:
        facility_mwh = Decimal("0")
        cbam_mwh = Decimal("0")
        facility_em = Decimal("0")
        cbam_em = Decimal("0")
        for _day, kwh, d, e in WORKBOOK_ELEC_MONTHS:
            pe = calculate_indirect_electricity_emissions(
                electricity_quantity=kwh,
                electricity_unit="kWh",
                factor_value=H4,
                factor_unit="tCO2e/MWh",
            )
            assert pe.ok and pe.electricity_mwh is not None
            assert pe.indirect_emissions_tco2e is not None
            share = monthly_cbam_share(total_production_tonnes=d, cbam_quantity_tonnes=e)
            attr_m = attribute_measure(pe.electricity_mwh, share)
            attr_e = attribute_measure(pe.indirect_emissions_tco2e, share)
            facility_mwh += attr_m.facility
            cbam_mwh += attr_m.cbam
            facility_em += attr_e.facility
            cbam_em += attr_e.cbam

        assert facility_mwh == GOLDEN_FACILITY_MWH_RAW
        assert abs(cbam_mwh - GOLDEN_CBAM_MWH_RAW) < Decimal("1e-40")
        assert facility_em == GOLDEN_FACILITY_EM_RAW
        assert abs(cbam_em - GOLDEN_CBAM_EM_RAW) < Decimal("1e-40")
        assert facility_mwh == cbam_mwh + (facility_mwh - cbam_mwh)
        assert facility_em == cbam_em + (facility_em - cbam_em)

        ids = [
            uuid.UUID("00000000-0000-0000-0000-000000000001"),
            uuid.UUID("00000000-0000-0000-0000-000000000002"),
            uuid.UUID("00000000-0000-0000-0000-000000000003"),
        ]
        groups = list(zip(ids, WORKBOOK_PRODUCT_TONNES, strict=True))
        elec_final, elec_rows = allocate_pool_with_largest_remainder(
            pool_raw=cbam_mwh, groups=groups
        )
        em_final, em_rows = allocate_pool_with_largest_remainder(pool_raw=cbam_em, groups=groups)
        assert elec_final == GOLDEN_CBAM_MWH_FINAL
        assert em_final == GOLDEN_CBAM_EM_FINAL
        assert sum(r.final_allocated for r in elec_rows) == elec_final
        assert sum(r.final_allocated for r in em_rows) == em_final
        assert elec_final - sum(r.final_allocated for r in elec_rows) == GOLDEN_REMAINING
        for row in elec_rows:
            assert row.final_allocated == WORKBOOK_PRODUCT_ELEC_FINALS[row.quantity]
        for row in em_rows:
            assert row.final_allocated == WORKBOOK_PRODUCT_EM_FINALS[row.quantity]
    finally:
        getcontext().prec = prior


def test_monthly_stage1_differs_from_period_wide_shortcut() -> None:
    facility = GOLDEN_FACILITY_MWH_RAW
    d_sum = sum(m[2] for m in WORKBOOK_ELEC_MONTHS)
    e_sum = sum(m[3] for m in WORKBOOK_ELEC_MONTHS)
    shortcut = facility * period_wide_shortcut_share(total_d=d_sum, total_e=e_sum)
    assert abs(shortcut - GOLDEN_CBAM_MWH_RAW) > Decimal("0.1")


def test_kwh_to_mwh_matches_workbook() -> None:
    assert kwh_to_mwh(Decimal("176034.53")) == Decimal("176.03453")
    assert to_mwh(Decimal("176.03453"), "MWh") == Decimal("176.03453")
    assert to_mwh(Decimal("176034.53"), "kWh") == Decimal("176.03453")


def test_deterministic_largest_remainder_tiebreak() -> None:
    pool = Decimal("1.00000000")
    a = uuid.UUID("00000000-0000-0000-0000-00000000000a")
    b = uuid.UUID("00000000-0000-0000-0000-00000000000b")
    first, rows1 = allocate_pool_with_largest_remainder(
        pool_raw=pool, groups=[(a, Decimal("1")), (b, Decimal("1"))]
    )
    second, rows2 = allocate_pool_with_largest_remainder(
        pool_raw=pool, groups=[(b, Decimal("1")), (a, Decimal("1"))]
    )
    assert first == second == Decimal("1.00000000")
    by_id1 = {r.group_id: r.final_allocated for r in rows1}
    by_id2 = {r.group_id: r.final_allocated for r in rows2}
    assert by_id1 == by_id2
    assert sum(by_id1.values()) == first


@pytest.mark.parametrize("zero_d", [True])
def test_zero_total_production_with_positive_e_raises(zero_d: bool) -> None:
    del zero_d
    with pytest.raises(ValueError, match="TOTAL_PRODUCTION_MUST_BE_POSITIVE"):
        monthly_cbam_share(total_production_tonnes=Decimal("0"), cbam_quantity_tonnes=Decimal("1"))
