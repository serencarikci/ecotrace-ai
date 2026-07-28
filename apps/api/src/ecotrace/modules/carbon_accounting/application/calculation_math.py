from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from ecotrace.core.carbon_constants import KG_CO2E_QUANTUM, KG_PER_TONNE, T_CO2E_QUANTUM


def q_kg(value: Decimal) -> Decimal:
    return value.quantize(KG_CO2E_QUANTUM, rounding=ROUND_HALF_UP)


def q_t(value: Decimal) -> Decimal:
    return value.quantize(T_CO2E_QUANTUM, rounding=ROUND_HALF_UP)


def kg_to_tonnes(kg: Decimal) -> Decimal:
    return q_t(kg / KG_PER_TONNE)


def calculate_direct_co2e(*, normalized_quantity: Decimal, factor_value: Decimal) -> Decimal:
    if normalized_quantity < 0 or factor_value < 0:
        raise ValueError("Quantity and factor must be non-negative.")
    return q_kg(normalized_quantity * factor_value)


def calculate_gas_specific(
    *,
    normalized_quantity: Decimal,
    co2_factor: Decimal | None,
    ch4_factor: Decimal | None,
    n2o_factor: Decimal | None,
    ch4_gwp: Decimal | None,
    n2o_gwp: Decimal | None,
    other_gas_co2e: Decimal = Decimal("0"),
) -> dict[str, Decimal]:
    for value in (normalized_quantity, co2_factor, ch4_factor, n2o_factor, other_gas_co2e):
        if value is not None and value < 0:
            raise ValueError("Factors and quantities must be non-negative.")

    co2_kg = q_kg(normalized_quantity * co2_factor) if co2_factor is not None else Decimal("0")
    ch4_kg = q_kg(normalized_quantity * ch4_factor) if ch4_factor is not None else Decimal("0")
    n2o_kg = q_kg(normalized_quantity * n2o_factor) if n2o_factor is not None else Decimal("0")

    ch4_co2e = Decimal("0")
    if ch4_kg and ch4_gwp is not None:
        ch4_co2e = q_kg(ch4_kg * ch4_gwp)
    n2o_co2e = Decimal("0")
    if n2o_kg and n2o_gwp is not None:
        n2o_co2e = q_kg(n2o_kg * n2o_gwp)

    total = q_kg(co2_kg + ch4_co2e + n2o_co2e + other_gas_co2e)
    return {
        "co2_kg": co2_kg,
        "ch4_kg": ch4_kg,
        "n2o_kg": n2o_kg,
        "ch4_kg_co2e": ch4_co2e,
        "n2o_kg_co2e": n2o_co2e,
        "other_gases_kg_co2e": q_kg(other_gas_co2e),
        "total_kg_co2e": total,
    }


def build_formula_explanation(
    *,
    mode: str,
    normalized_quantity: Decimal,
    normalized_unit: str,
    factor_value: Decimal | None = None,
    factor_unit: str | None = None,
    gas_parts: dict[str, Decimal] | None = None,
) -> str:
    if mode == "direct":
        assert factor_value is not None and factor_unit is not None
        total = calculate_direct_co2e(
            normalized_quantity=normalized_quantity, factor_value=factor_value
        )
        return (
            f"totalKgCO2e = {normalized_quantity} {normalized_unit} x "
            f"{factor_value} {factor_unit} = {total} kgCO2e"
        )
    assert gas_parts is not None
    return (
        "totalKgCO2e = co2Kg + (ch4Kg x ch4Gwp) + (n2oKg x n2oGwp) + otherGasCO2e = "
        f"{gas_parts['total_kg_co2e']} kgCO2e"
    )


def compute_emission_result(
    *,
    normalized_quantity: Decimal,
    normalized_unit_code: str,
    factor_value: Decimal | None,
    factor_unit_code: str,
    co2_factor: Decimal | None,
    ch4_factor: Decimal | None,
    n2o_factor: Decimal | None,
    biogenic_co2_factor: Decimal | None,
    ch4_gwp: Decimal | None,
    n2o_gwp: Decimal | None,
    other_gases_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    other_co2e = Decimal("0")
    if other_gases_json:
        for _code, payload in other_gases_json.items():
            if isinstance(payload, dict) and "kgCO2e" in payload:
                other_co2e += Decimal(str(payload["kgCO2e"]))
            elif isinstance(payload, (int, float, str, Decimal)):
                other_co2e += Decimal(str(payload))

    has_gas = any(v is not None for v in (co2_factor, ch4_factor, n2o_factor))
    if has_gas:
        parts = calculate_gas_specific(
            normalized_quantity=normalized_quantity,
            co2_factor=co2_factor,
            ch4_factor=ch4_factor,
            n2o_factor=n2o_factor,
            ch4_gwp=ch4_gwp,
            n2o_gwp=n2o_gwp,
            other_gas_co2e=other_co2e,
        )

        formula = build_formula_explanation(
            mode="gas",
            normalized_quantity=normalized_quantity,
            normalized_unit=normalized_unit_code,
            gas_parts=parts,
        )
        biogenic = (
            q_kg(normalized_quantity * biogenic_co2_factor)
            if biogenic_co2_factor is not None
            else Decimal("0")
        )
        return {
            "mode": "gas_specific",
            "co2_kg": parts["co2_kg"],
            "ch4_kg": parts["ch4_kg"],
            "n2o_kg": parts["n2o_kg"],
            "biogenic_co2_kg": biogenic,
            "total_kg_co2e": parts["total_kg_co2e"],
            "total_t_co2e": kg_to_tonnes(parts["total_kg_co2e"]),
            "formula": formula,
            "other_gases_json": other_gases_json,
        }

    if factor_value is None:
        raise ValueError("Either factor_value or gas-specific factors are required.")
    total = calculate_direct_co2e(
        normalized_quantity=normalized_quantity, factor_value=factor_value
    )
    biogenic = (
        q_kg(normalized_quantity * biogenic_co2_factor)
        if biogenic_co2_factor is not None
        else Decimal("0")
    )
    formula = build_formula_explanation(
        mode="direct",
        normalized_quantity=normalized_quantity,
        normalized_unit=normalized_unit_code,
        factor_value=factor_value,
        factor_unit=factor_unit_code,
    )
    return {
        "mode": "direct",
        "co2_kg": None,
        "ch4_kg": None,
        "n2o_kg": None,
        "biogenic_co2_kg": biogenic,
        "total_kg_co2e": total,
        "total_t_co2e": kg_to_tonnes(total),
        "formula": formula,
        "other_gases_json": other_gases_json,
    }
