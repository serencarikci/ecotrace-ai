"""Post-recalculation OUTPUT parity vs EcoTrace snapshots (fail with cell detail)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_FORMULA_PARITY_FAILED,
)
from ecotrace.modules.cbam.application.official_see_export.mapping.loader import MappingManifest

_FORMULA_ERROR_TOKENS = ('#N/A', '#NAME?', '#VALUE?', '#REF!', '#DIV/0!', '#NUM?', '#NULL!')

# Official SEE Summary_Products I/J/K (and Communication mirrors) use Excel format ``0.000``.
_SEE_SPECIFIC_NUM_FMT = '0.000'
_SEE_SPECIFIC_PLACES = 3

_SUMMARY_PRODUCTS_SEE_COLS = ('F', 'I', 'J', 'K', 'P')
_SUMMARY_COMM_SEE_COLS = ('F', 'G', 'I', 'J', 'K')
_SUMMARY_PRODUCTS_FIRST_ROW = 10
_SUMMARY_COMM_FIRST_ROW = 26
_SUMMARY_MAX_PRODUCT_SLOTS = 10


@dataclass(frozen=True, slots=True)
class ParityMismatch:
    sheet: str
    cell: str
    expected: str
    actual: str
    diff: str
    semantic_field: str


def workbook_places_for_cell(num_fmt: str | None) -> int:
    """Derive comparison decimal places from an Excel number format.

    Official SEE Summary_Products / Summary_Communication specific-emissions cells use
    ``0.000`` → **3** places. Do not invent a looser tolerance than the format implies.
    """
    fmt = (num_fmt or '').strip()
    if not fmt or fmt in {'General', '@', 'text'}:
        return 0
    # Patterns like 0.000, #,##0.000, 0.00%
    match = re.search(r'\.(0+)', fmt)
    if match:
        return len(match.group(1))
    return 0


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == '':
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except InvalidOperation:
            return None
    return None


def _is_formula_error(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    upper = value.strip().upper()
    return any(tok in upper for tok in _FORMULA_ERROR_TOKENS)


def _quantize_equal(expected: Decimal, actual: Decimal, *, places: int) -> bool:
    if places <= 0:
        return expected == actual
    quant = Decimal('1').scaleb(-places)
    return bool(
        expected.quantize(quant, rounding=ROUND_HALF_UP)
        == actual.quantize(quant, rounding=ROUND_HALF_UP)
    )


def _values_equal(expected: Any, actual: Any, *, places: int) -> bool:
    exp_d = _to_decimal(expected)
    act_d = _to_decimal(actual)
    if exp_d is not None and act_d is not None:
        return _quantize_equal(exp_d, act_d, places=places)
    return bool(expected == actual)


def _formula_error_finding(
    sheet: str,
    cell: str,
    actual: Any,
    *,
    semantic_field: str,
) -> ParityMismatch:
    return ParityMismatch(
        sheet=sheet,
        cell=cell,
        expected='<non-error>',
        actual=repr(actual),
        diff='formula_error',
        semantic_field=semantic_field,
    )


def compare_outputs(
    recalculated_xlsx: Path,
    manifest: MappingManifest,
    expected_by_key: dict[tuple[str, str], Any],
    *,
    places: int | None = None,
) -> list[ParityMismatch]:
    """Open data_only workbook and compare OUTPUT cells to EcoTrace expected values.

    When ``places`` is None, each cell uses ``workbook_places_for_cell`` of its number
    format (``0.000`` → 3). Explicit ``places`` overrides for all cells (tests).
    """
    wb = load_workbook(recalculated_xlsx, data_only=True)
    wb_fmt = load_workbook(recalculated_xlsx, data_only=False)
    mismatches: list[ParityMismatch] = []
    for entry in manifest.by_direction('OUTPUT'):
        key = (entry.sheet, entry.cell)
        if entry.sheet not in wb.sheetnames:
            if key in expected_by_key or entry.required:
                mismatches.append(
                    ParityMismatch(
                        sheet=entry.sheet,
                        cell=entry.cell,
                        expected=repr(expected_by_key.get(key)),
                        actual='<missing sheet>',
                        diff='n/a',
                        semantic_field=entry.semantic_field,
                    )
                )
            continue
        actual = wb[entry.sheet][entry.cell].value
        if _is_formula_error(actual):
            mismatches.append(
                _formula_error_finding(
                    entry.sheet,
                    entry.cell,
                    actual,
                    semantic_field=entry.semantic_field,
                )
            )
            continue
        if key not in expected_by_key:
            continue
        expected = expected_by_key[key]
        cell_places = places
        if cell_places is None:
            num_fmt = wb_fmt[entry.sheet][entry.cell].number_format
            cell_places = workbook_places_for_cell(num_fmt)
            if cell_places <= 0:
                cell_places = 8
        if _values_equal(expected, actual, places=cell_places):
            continue
        exp_d = _to_decimal(expected)
        act_d = _to_decimal(actual)
        diff = (
            str(act_d - exp_d)
            if exp_d is not None and act_d is not None
            else 'n/a'
        )
        mismatches.append(
            ParityMismatch(
                sheet=entry.sheet,
                cell=entry.cell,
                expected=repr(expected),
                actual=repr(actual),
                diff=diff,
                semantic_field=entry.semantic_field,
            )
        )
    return mismatches


def scan_output_formula_errors(
    recalculated_xlsx: Path,
    manifest: MappingManifest,
    *,
    product_count: int | None = None,
) -> list[ParityMismatch]:
    """Fail when OUTPUT / SEE summary cells show Excel error tokens after recalc.

    Scans:
    - all manifest OUTPUT cells
    - Summary_Communication product block F/G/I/J/K for used product rows
    - Summary_Products F/I/J/K/P for used product slots
    """
    wb = load_workbook(recalculated_xlsx, data_only=True)
    findings: list[ParityMismatch] = []
    seen: set[tuple[str, str]] = set()

    def _check(sheet: str, cell: str, *, semantic_field: str) -> None:
        key = (sheet, cell)
        if key in seen:
            return
        seen.add(key)
        if sheet not in wb.sheetnames:
            return
        actual = wb[sheet][cell].value
        if _is_formula_error(actual):
            findings.append(
                _formula_error_finding(sheet, cell, actual, semantic_field=semantic_field)
            )

    for entry in manifest.by_direction('OUTPUT'):
        _check(entry.sheet, entry.cell, semantic_field=entry.semantic_field)

    used = product_count
    if used is None:
        used = 0
        if 'Summary_Products' in wb.sheetnames:
            sp = wb['Summary_Products']
            for i in range(_SUMMARY_MAX_PRODUCT_SLOTS):
                row = _SUMMARY_PRODUCTS_FIRST_ROW + i
                if sp[f'D{row}'].value not in (None, ''):
                    used = i + 1
        if used == 0:
            used = _SUMMARY_MAX_PRODUCT_SLOTS

    for i in range(max(0, used)):
        prod_row = _SUMMARY_PRODUCTS_FIRST_ROW + i
        comm_row = _SUMMARY_COMM_FIRST_ROW + i
        for col in _SUMMARY_PRODUCTS_SEE_COLS:
            _check(
                'Summary_Products',
                f'{col}{prod_row}',
                semantic_field=f'summary_products[{i}].scan.{col.lower()}',
            )
        for col in _SUMMARY_COMM_SEE_COLS:
            _check(
                'Summary_Communication',
                f'{col}{comm_row}',
                semantic_field=f'summary_communication[{i}].scan.{col.lower()}',
            )

    return findings


def assert_no_formula_errors_or_raise(
    recalculated_xlsx: Path,
    manifest: MappingManifest,
    *,
    product_count: int | None = None,
) -> None:
    findings = scan_output_formula_errors(
        recalculated_xlsx, manifest, product_count=product_count
    )
    if not findings:
        return
    first = findings[0]
    raise BusinessRuleError(
        (
            f'Formula error token at {first.sheet}!{first.cell}: '
            f'actual={first.actual}'
        ),
        code=CODE_FORMULA_PARITY_FAILED,
        details=[
            {
                'code': CODE_FORMULA_PARITY_FAILED,
                'sheet': m.sheet,
                'cell': m.cell,
                'expected': m.expected,
                'actual': m.actual,
                'diff': m.diff,
                'semanticField': m.semantic_field,
            }
            for m in findings[:50]
        ],
    )


def assert_parity_or_raise(
    recalculated_xlsx: Path,
    manifest: MappingManifest,
    expected_by_key: dict[tuple[str, str], Any],
) -> None:
    mismatches = compare_outputs(recalculated_xlsx, manifest, expected_by_key)
    if not mismatches:
        return
    first = mismatches[0]
    raise BusinessRuleError(
        (
            f'Formula parity failed at {first.sheet}!{first.cell}: '
            f'expected={first.expected} actual={first.actual} diff={first.diff}'
        ),
        code=CODE_FORMULA_PARITY_FAILED,
        details=[
            {
                'code': CODE_FORMULA_PARITY_FAILED,
                'sheet': m.sheet,
                'cell': m.cell,
                'expected': m.expected,
                'actual': m.actual,
                'diff': m.diff,
                'semanticField': m.semantic_field,
            }
            for m in mismatches[:50]
        ],
    )


# Documented constant for acceptance tests / reports.
SEE_IJK_NUMBER_FORMAT = _SEE_SPECIFIC_NUM_FMT
SEE_IJK_DECIMAL_PLACES = _SEE_SPECIFIC_PLACES
