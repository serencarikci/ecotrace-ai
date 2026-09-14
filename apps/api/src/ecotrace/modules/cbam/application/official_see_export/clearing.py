"""Clear CLEAR_EXAMPLE / unused INPUT slots before writing EcoTrace values."""

from __future__ import annotations

from openpyxl.workbook.workbook import Workbook

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_FORMULA_PRESERVATION_FAILED,
)
from ecotrace.modules.cbam.application.official_see_export.mapping.loader import (
    ManifestEntry,
    MappingManifest,
)


def _is_formula(value: object | None) -> bool:
    return isinstance(value, str) and value.startswith("=")


def clear_example_and_unused_inputs(
    wb: Workbook,
    manifest: MappingManifest,
    *,
    used_input_keys: set[tuple[str, str]],
) -> int:
    """Clear all CLEAR_EXAMPLE cells and unused INPUT slots.

    Never clears FORMULA/OUTPUT/PRESERVE/CONTROL cells. Refuses to clear a formula.
    ``used_input_keys`` is the set of (sheet, cell) that will receive EcoTrace INPUT.
    """
    cleared = 0
    clear_entries = list(manifest.by_direction("CLEAR_EXAMPLE"))
    input_entries = list(manifest.by_direction("INPUT"))

    for entry in clear_entries:
        cleared += _clear_cell(wb, entry)

    for entry in input_entries:
        key = (entry.sheet, entry.cell)
        if key in used_input_keys:
            continue
        # Unused mapped INPUT slots must be empty so example data cannot linger.
        cleared += _clear_cell(wb, entry)

    return cleared


def _clear_cell(wb: Workbook, entry: ManifestEntry) -> int:
    if entry.sheet not in wb.sheetnames:
        return 0
    ws = wb[entry.sheet]
    cell = ws[entry.cell]
    if _is_formula(cell.value):
        # CLEAR_EXAMPLE entries that collide with formulas are skipped (manifest hygiene).
        # Unused INPUT must never clear a formula — that is a mapping bug.
        if entry.direction == "CLEAR_EXAMPLE":
            return 0
        raise BusinessRuleError(
            f"Refusing to clear formula cell {entry.sheet}!{entry.cell}",
            code=CODE_FORMULA_PRESERVATION_FAILED,
            details=[
                {
                    "code": CODE_FORMULA_PRESERVATION_FAILED,
                    "sheet": entry.sheet,
                    "cell": entry.cell,
                }
            ],
        )
    if cell.value is None:
        return 0
    cell.value = None
    return 1
