"""Capacity checks for Official SEE workbook slots (fail-closed, no silent truncate)."""

from __future__ import annotations

from dataclasses import dataclass

from ecotrace.modules.cbam.application.official_see_export.constants import (
    CAPACITY_FUEL_ACTIVITIES,
    CAPACITY_GOODS,
    CAPACITY_INSTALLATIONS,
    CAPACITY_PRECURSOR_PRODUCT_USE_ROWS,
    CAPACITY_PRECURSORS,
    CAPACITY_PROCESS_PRODUCT_USE_ROWS,
    CAPACITY_PROCESSES,
    CODE_CAPACITY_EXCEEDED_FUELS,
    CODE_CAPACITY_EXCEEDED_GOODS,
    CODE_CAPACITY_EXCEEDED_INSTALLATIONS,
    CODE_CAPACITY_EXCEEDED_PRECURSOR_USES,
    CODE_CAPACITY_EXCEEDED_PRECURSORS,
    CODE_CAPACITY_EXCEEDED_PROCESS_USES,
    CODE_CAPACITY_EXCEEDED_PROCESSES,
)


@dataclass(frozen=True, slots=True)
class CapacityUsage:
    installations: int
    goods: int
    processes: int
    precursors: int
    max_process_product_uses: int
    max_precursor_product_uses: int
    fuel_activities: int


@dataclass(frozen=True, slots=True)
class CapacityLimits:
    installations: int = CAPACITY_INSTALLATIONS
    goods: int = CAPACITY_GOODS
    processes: int = CAPACITY_PROCESSES
    precursors: int = CAPACITY_PRECURSORS
    process_product_use_rows: int = CAPACITY_PROCESS_PRODUCT_USE_ROWS
    precursor_product_use_rows: int = CAPACITY_PRECURSOR_PRODUCT_USE_ROWS
    fuel_activities: int = CAPACITY_FUEL_ACTIVITIES


def assess_capacity(
    usage: CapacityUsage,
    *,
    limits: CapacityLimits | None = None,
) -> list[str]:
    """Return stable CAPACITY_EXCEEDED_* codes for any overflow (never truncate)."""
    lim = limits or CapacityLimits()
    codes: list[str] = []
    if usage.installations > lim.installations:
        codes.append(CODE_CAPACITY_EXCEEDED_INSTALLATIONS)
    if usage.goods > lim.goods:
        codes.append(CODE_CAPACITY_EXCEEDED_GOODS)
    if usage.processes > lim.processes:
        codes.append(CODE_CAPACITY_EXCEEDED_PROCESSES)
    if usage.precursors > lim.precursors:
        codes.append(CODE_CAPACITY_EXCEEDED_PRECURSORS)
    if usage.max_process_product_uses > lim.process_product_use_rows:
        codes.append(CODE_CAPACITY_EXCEEDED_PROCESS_USES)
    if usage.max_precursor_product_uses > lim.precursor_product_use_rows:
        codes.append(CODE_CAPACITY_EXCEEDED_PRECURSOR_USES)
    if usage.fuel_activities > lim.fuel_activities:
        codes.append(CODE_CAPACITY_EXCEEDED_FUELS)
    return codes
