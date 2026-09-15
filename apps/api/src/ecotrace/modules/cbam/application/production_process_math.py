"""Product-quantity distribution balance and heat/waste-gas math (Phase 9A)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ecotrace.modules.cbam.application.production_process_constants import (
    BALANCE_BALANCED,
    BALANCE_INCOMPLETE,
    BALANCE_UNBALANCED,
    CONST_EF_NAT_GAS_TCO2_PER_TJ,
    EXPORTED_ELECTRICITY_CALC_STATUS_CALCULATED,
    EXPORTED_ELECTRICITY_CALC_STATUS_INCOMPLETE,
    EXPORTED_ELECTRICITY_CALC_STATUS_NOT_APPLICABLE,
    EXPORTED_ELECTRICITY_FORMULA_REF,
    HEAT_CALC_STATUS_CALCULATED,
    HEAT_CALC_STATUS_INCOMPLETE,
    HEAT_CALC_STATUS_NOT_APPLICABLE,
    WASTE_GAS_CALC_STATUS_CALCULATED,
    WASTE_GAS_CALC_STATUS_INCOMPLETE,
    WASTE_GAS_CALC_STATUS_NOT_APPLICABLE,
    WASTE_GAS_EXPORT_FACTOR,
)


@dataclass(frozen=True, slots=True)
class DistributionBalance:
    produced_tonnes: Decimal | None
    marketed_tonnes: Decimal | None
    other_cbam_tonnes: Decimal
    non_cbam_tonnes: Decimal | None
    distributed_tonnes: Decimal | None
    remaining_tonnes: Decimal | None
    balance_status: str
    all_to_market: bool | None
    market_share: Decimal | None


def compute_distribution_balance(
    *,
    produced_tonnes: Decimal | None,
    marketed_tonnes: Decimal | None,
    other_cbam_tonnes: Decimal,
    non_cbam_tonnes: Decimal | None,
) -> DistributionBalance:
    """Exact Decimal balance (no business rounding tolerance).

    Workbook: L42 = L24 - SUM(L27, L32:L41)
    """
    if produced_tonnes is None or marketed_tonnes is None or non_cbam_tonnes is None:
        return DistributionBalance(
            produced_tonnes=produced_tonnes,
            marketed_tonnes=marketed_tonnes,
            other_cbam_tonnes=other_cbam_tonnes,
            non_cbam_tonnes=non_cbam_tonnes,
            distributed_tonnes=None,
            remaining_tonnes=None,
            balance_status=BALANCE_INCOMPLETE,
            all_to_market=None,
            market_share=None,
        )

    distributed = marketed_tonnes + other_cbam_tonnes + non_cbam_tonnes
    remaining = produced_tonnes - distributed
    balanced = remaining == Decimal("0")
    market_share: Decimal | None = None
    all_to_market: bool | None = None
    if produced_tonnes > 0:
        market_share = marketed_tonnes / produced_tonnes
        all_to_market = produced_tonnes == marketed_tonnes
    elif produced_tonnes == 0:
        all_to_market = marketed_tonnes == 0
        market_share = None

    return DistributionBalance(
        produced_tonnes=produced_tonnes,
        marketed_tonnes=marketed_tonnes,
        other_cbam_tonnes=other_cbam_tonnes,
        non_cbam_tonnes=non_cbam_tonnes,
        distributed_tonnes=distributed,
        remaining_tonnes=remaining,
        balance_status=BALANCE_BALANCED if balanced else BALANCE_UNBALANCED,
        all_to_market=all_to_market,
        market_share=market_share,
    )


@dataclass(frozen=True, slots=True)
class HeatAttribution:
    status: str
    attributed_tco2: Decimal | None
    formula_ref: str | None


def compute_measurable_heat_attribution(
    *,
    has_measurable_heat: bool | None,
    imported_tj: Decimal | None,
    exported_tj: Decimal | None,
    imported_ef: Decimal | None,
    exported_ef: Decimal | None,
) -> HeatAttribution:
    """Workbook T58 = L57*L58 - M57*M58."""
    if has_measurable_heat is not True:
        return HeatAttribution(
            status=HEAT_CALC_STATUS_NOT_APPLICABLE,
            attributed_tco2=None,
            formula_ref=None,
        )
    if None in (imported_tj, exported_tj, imported_ef, exported_ef):
        return HeatAttribution(
            status=HEAT_CALC_STATUS_INCOMPLETE,
            attributed_tco2=None,
            formula_ref="D_Processes!T58=L57*L58-M57*M58",
        )
    assert imported_tj is not None and exported_tj is not None
    assert imported_ef is not None and exported_ef is not None
    value = imported_tj * imported_ef - exported_tj * exported_ef
    return HeatAttribution(
        status=HEAT_CALC_STATUS_CALCULATED,
        attributed_tco2=value,
        formula_ref="D_Processes!T58=L57*L58-M57*M58",
    )


@dataclass(frozen=True, slots=True)
class WasteGasAttribution:
    status: str
    attributed_tco2: Decimal | None
    formula_ref: str | None
    ef_tco2_per_tj: Decimal | None
    note: str | None


def compute_waste_gas_attribution(
    *,
    has_waste_gas: bool | None,
    imported_tj: Decimal | None,
    exported_tj: Decimal | None,
) -> WasteGasAttribution:
    """Workbook T62 = L61*CONST_EFNatGas - M61*CONST_EFNatGas*0.667.

    L62/M62 are decimal-validated UI cells but are not referenced by T62.
    """
    if has_waste_gas is not True:
        return WasteGasAttribution(
            status=WASTE_GAS_CALC_STATUS_NOT_APPLICABLE,
            attributed_tco2=None,
            formula_ref=None,
            ef_tco2_per_tj=None,
            note=None,
        )
    if imported_tj is None or exported_tj is None:
        return WasteGasAttribution(
            status=WASTE_GAS_CALC_STATUS_INCOMPLETE,
            attributed_tco2=None,
            formula_ref="D_Processes!T62=L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667",
            ef_tco2_per_tj=CONST_EF_NAT_GAS_TCO2_PER_TJ,
            note="L62/M62 not used by workbook T62; CONST_EFNatGas=56.1 applies.",
        )
    ef = CONST_EF_NAT_GAS_TCO2_PER_TJ
    value = imported_tj * ef - exported_tj * ef * WASTE_GAS_EXPORT_FACTOR
    return WasteGasAttribution(
        status=WASTE_GAS_CALC_STATUS_CALCULATED,
        attributed_tco2=value,
        formula_ref="D_Processes!T62=L61*CONST_EFNatGas-M61*CONST_EFNatGas*0.667",
        ef_tco2_per_tj=ef,
        note="L62/M62 not used by workbook T62; CONST_EFNatGas=56.1 applies.",
    )


@dataclass(frozen=True, slots=True)
class ExportedElectricityAttribution:
    status: str
    attributed_direct_tco2e: Decimal | None
    formula_ref: str | None


def compute_exported_electricity_attribution(
    *,
    has_exported_electricity: bool | None,
    quantity_mwh: Decimal | None,
    emission_factor: Decimal | None,
) -> ExportedElectricityAttribution:
    """Workbook T72 = -L71*L72 — exported electricity reduces attributed direct emissions.

    The result is zero or negative and is never derived from a facility-level
    purchased-electricity export figure.
    """
    if has_exported_electricity is not True:
        return ExportedElectricityAttribution(
            status=EXPORTED_ELECTRICITY_CALC_STATUS_NOT_APPLICABLE,
            attributed_direct_tco2e=None,
            formula_ref=None,
        )
    if quantity_mwh is None or emission_factor is None:
        return ExportedElectricityAttribution(
            status=EXPORTED_ELECTRICITY_CALC_STATUS_INCOMPLETE,
            attributed_direct_tco2e=None,
            formula_ref=EXPORTED_ELECTRICITY_FORMULA_REF,
        )
    if quantity_mwh < Decimal("0") or emission_factor < Decimal("0"):
        raise ValueError("EXPORTED_ELECTRICITY_NEGATIVE")
    return ExportedElectricityAttribution(
        status=EXPORTED_ELECTRICITY_CALC_STATUS_CALCULATED,
        attributed_direct_tco2e=-(quantity_mwh * emission_factor),
        formula_ref=EXPORTED_ELECTRICITY_FORMULA_REF,
    )
