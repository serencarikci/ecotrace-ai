"""Surgical XLSX ZIP/XML cell patching — preserves CF extLst and other package parts."""

from __future__ import annotations

import re
import zipfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_FORMULA_PRESERVATION_FAILED,
)
from ecotrace.modules.cbam.application.official_see_export.package_inventory import (
    sheet_name_to_path,
)
from ecotrace.modules.cbam.application.official_see_export.security import excel_safe_text

# Cell reference → column letters + row number
_CELL_REF_RE = re.compile(r'^([A-Z]+)(\d+)$')
# Match a single <c r="A1" .../> or <c r="A1" ...>...</c>
# IMPORTANT: [^>]* must not swallow the '/' of self-closing tags before we require '/>'.
_CELL_PATTERN_TMPL = r'<c r="{ref}"[^>]*?/>|<c r="{ref}"[^>]*>.*?</c>'
_ROW_PATTERN_TMPL = r'(<row(?=[^>]*\sr="{row}"[\s>])[^>]*>)(.*?)(</row>)'
_SST_COUNT_RE = re.compile(r'(<sst\b)([^>]*)(>)')
_INLINE_CELL_RE = re.compile(r'<c r="([A-Z]+)(\d+)"[^>]*?/>|<c r="([A-Z]+)(\d+)"[^>]*>.*?</c>', re.DOTALL)


def _col_index(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord('A') + 1)
    return n


def _parse_ref(ref: str) -> tuple[str, int]:
    m = _CELL_REF_RE.match(ref.upper())
    if not m:
        raise ValueError(f'Invalid cell ref: {ref}')
    return m.group(1), int(m.group(2))


def _extract_style(cell_xml: str) -> str | None:
    m = re.search(r'\ss="(\d+)"', cell_xml)
    return m.group(1) if m else None


def _cell_has_formula(cell_xml: str) -> bool:
    return bool(re.search(r'<f(?:\s|/|>)', cell_xml))


def _excel_serial(value: date | datetime) -> float:
    if isinstance(value, datetime):
        d = value.date()
        fraction = (
            value.hour * 3600 + value.minute * 60 + value.second + value.microsecond / 1e6
        ) / 86400.0
    else:
        d = value
        fraction = 0.0
    # Excel's 1900 date system epoch (with Lotus leap-year bug compatibility).
    epoch = date(1899, 12, 30)
    return float((d - epoch).days) + fraction


def coerce_cell_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        if len(value) == 10 and value[4] == '-' and value[7] == '-':
            try:
                return date.fromisoformat(value)
            except ValueError:
                pass
        return excel_safe_text(value)
    if isinstance(value, bool):
        return value
    return value


class SharedStringTable:
    """In-memory sharedStrings.xml editor (append-only for new strings)."""

    def __init__(self, xml: bytes) -> None:
        self._text = xml.decode('utf-8')
        self._index: dict[str, int] = {}
        self._count = 0
        # Build index from existing <si> entries (simple <t> text only + rich text concat).
        for i, si in enumerate(re.findall(r'<si>(.*?)</si>', self._text, flags=re.DOTALL)):
            texts = re.findall(r'<t(?:\s[^>]*)?>(.*?)</t>', si, flags=re.DOTALL)
            joined = ''.join(_xml_unescape(t) for t in texts)
            if joined not in self._index:
                self._index[joined] = i
            self._count = i + 1

    def get_or_add(self, value: str) -> int:
        if value in self._index:
            return self._index[value]
        idx = self._count
        self._index[value] = idx
        self._count += 1
        escaped = escape(value)
        # Preserve xml:space when leading/trailing whitespace.
        if value != value.strip():
            si = f'<si><t xml:space="preserve">{escaped}</t></si>'
        else:
            si = f'<si><t>{escaped}</t></si>'
        if '</sst>' not in self._text:
            raise BusinessRuleError('sharedStrings.xml missing </sst>')
        self._text = self._text.replace('</sst>', si + '</sst>', 1)
        self._text = _SST_COUNT_RE.sub(
            lambda m: f'{m.group(1)}{_update_sst_attrs(m.group(2), self._count)}{m.group(3)}',
            self._text,
            count=1,
        )
        return idx

    def dumps(self) -> bytes:
        return self._text.encode('utf-8')


def _xml_unescape(text: str) -> str:
    return (
        text.replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&quot;', '"')
        .replace('&apos;', "'")
        .replace('&amp;', '&')
    )


def _update_sst_attrs(attrs: str, count: int) -> str:
    attrs2 = re.sub(r'\bcount="\d+"', f'count="{count}"', attrs)
    if 'count="' not in attrs2:
        attrs2 = f' count="{count}"' + attrs2
    attrs2 = re.sub(r'\buniqueCount="\d+"', f'uniqueCount="{count}"', attrs2)
    if 'uniqueCount="' not in attrs2:
        attrs2 = attrs2 + f' uniqueCount="{count}"'
    return attrs2


def _build_cell_xml(ref: str, value: Any, *, style: str | None, sst: SharedStringTable) -> str:
    style_attr = f' s="{style}"' if style is not None else ''
    if value is None:
        return f'<c r="{ref}"{style_attr}/>'
    if isinstance(value, bool):
        return f'<c r="{ref}"{style_attr} t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (date, datetime)):
        serial = _excel_serial(value)
        return f'<c r="{ref}"{style_attr}><v>{serial}</v></c>'
    if isinstance(value, (int, float)):
        # Avoid scientific notation surprises for ints.
        if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            rendered = str(int(value))
        else:
            rendered = repr(float(value)) if isinstance(value, float) else str(value)
            # Prefer compact decimal.
            if isinstance(value, float):
                rendered = format(value, 'g')
                if rendered == '-0':
                    rendered = '0'
        return f'<c r="{ref}"{style_attr}><v>{rendered}</v></c>'
    text = str(value)
    idx = sst.get_or_add(text)
    return f'<c r="{ref}"{style_attr} t="s"><v>{idx}</v></c>'


def _set_cell_in_sheet(sheet_xml: str, ref: str, new_cell: str, *, allow_formula: bool) -> str:
    pattern = re.compile(_CELL_PATTERN_TMPL.format(ref=re.escape(ref)), re.DOTALL)
    match = pattern.search(sheet_xml)
    if match:
        old = match.group(0)
        if _cell_has_formula(old) and not allow_formula:
            raise BusinessRuleError(
                f'Refusing to overwrite formula cell {ref}',
                code=CODE_FORMULA_PRESERVATION_FAILED,
                details=[{'code': CODE_FORMULA_PRESERVATION_FAILED, 'cell': ref}],
            )
        return sheet_xml[: match.start()] + new_cell + sheet_xml[match.end() :]

    col, row = _parse_ref(ref)
    row_pat = re.compile(_ROW_PATTERN_TMPL.format(row=row), re.DOTALL)
    row_m = row_pat.search(sheet_xml)
    if not row_m:
        # Sparse template: create a minimal row before </sheetData>
        row_xml = f'<row r="{row}">{new_cell}</row>'
        if '</sheetData>' not in sheet_xml:
            raise BusinessRuleError(f'sheetData missing while inserting {ref}')
        return sheet_xml.replace('</sheetData>', row_xml + '</sheetData>', 1)

    prefix, body, suffix = row_m.group(1), row_m.group(2), row_m.group(3)
    # Insert in column order among existing cells.
    cells = list(_INLINE_CELL_RE.finditer(body))
    insert_at = len(body)
    target_idx = _col_index(col)
    for cm in cells:
        c_col = cm.group(1) or cm.group(3)
        if _col_index(c_col) > target_idx:
            insert_at = cm.start()
            break
        insert_at = cm.end()
    new_body = body[:insert_at] + new_cell + body[insert_at:]
    rebuilt = prefix + new_body + suffix
    return sheet_xml[: row_m.start()] + rebuilt + sheet_xml[row_m.end() :]


def _ensure_full_calc_on_load(workbook_xml: bytes) -> bytes:
    text = workbook_xml.decode('utf-8')
    if re.search(r'<calcPr\b[^>]*/>', text):
        def _patch(m: re.Match[str]) -> str:
            tag = m.group(0)
            if 'fullCalcOnLoad' in tag:
                tag = re.sub(r'fullCalcOnLoad="[^"]*"', 'fullCalcOnLoad="1"', tag)
            else:
                tag = tag.replace('/>', ' fullCalcOnLoad="1"/>')
            if 'calcMode=' not in tag:
                tag = tag.replace('/>', ' calcMode="auto"/>')
            return tag

        text = re.sub(r'<calcPr\b[^>]*/>', _patch, text, count=1)
    elif '<calcPr' in text:
        text = re.sub(
            r'(<calcPr\b[^>]*)(>)',
            lambda m: (
                m.group(1)
                + (' fullCalcOnLoad="1"' if 'fullCalcOnLoad' not in m.group(1) else '')
                + m.group(2)
            ),
            text,
            count=1,
        )
    else:
        # Insert before </workbook>
        text = text.replace(
            '</workbook>',
            '<calcPr calcMode="auto" fullCalcOnLoad="1"/></workbook>',
            1,
        )
    return text.encode('utf-8')


def apply_cell_patches(
    *,
    template_path: Path,
    output_path: Path,
    patches: dict[tuple[str, str], Any | None],
    set_full_calc_on_load: bool = True,
) -> dict[str, Any]:
    """Copy template ZIP and surgically set/clear cells.

    ``patches`` maps (sheet_name, cell_ref) → value (None clears the cell).
    Unmodified package parts keep identical uncompressed bytes.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(template_path, 'r') as zin:
        name_to_path = sheet_name_to_path(
            zin.read('xl/workbook.xml'),
            zin.read('xl/_rels/workbook.xml.rels'),
        )
        sst = SharedStringTable(zin.read('xl/sharedStrings.xml'))

        # Group patches by sheet path
        by_sheet: dict[str, dict[str, Any | None]] = {}
        unknown_sheets: list[str] = []
        for (sheet, cell), value in patches.items():
            path = name_to_path.get(sheet)
            if path is None:
                unknown_sheets.append(sheet)
                continue
            by_sheet.setdefault(path, {})[cell.upper()] = coerce_cell_value(value)
        if unknown_sheets:
            raise BusinessRuleError(
                f'Worksheet missing: {sorted(set(unknown_sheets))[0]}',
            )

        sheet_blobs: dict[str, bytes] = {}
        cleared = 0
        written = 0
        for path, cells in by_sheet.items():
            xml = zin.read(path).decode('utf-8')
            for ref, value in cells.items():
                pattern = re.compile(
                    _CELL_PATTERN_TMPL.format(ref=re.escape(ref)), re.DOTALL
                )
                match = pattern.search(xml)
                style = _extract_style(match.group(0)) if match else None
                if match and _cell_has_formula(match.group(0)):
                    if value is None:
                        # CLEAR_EXAMPLE colliding with a formula: skip (manifest hygiene).
                        continue
                    raise BusinessRuleError(
                        f'Refusing to overwrite formula cell {path}!{ref}',
                        code=CODE_FORMULA_PRESERVATION_FAILED,
                        details=[
                            {
                                'code': CODE_FORMULA_PRESERVATION_FAILED,
                                'sheet_path': path,
                                'cell': ref,
                            }
                        ],
                    )
                if value is None:
                    if match is None:
                        continue
                    # Clear: keep style shell so formatting survives.
                    new_cell = _build_cell_xml(ref, None, style=style, sst=sst)
                    xml = _set_cell_in_sheet(xml, ref, new_cell, allow_formula=False)
                    cleared += 1
                else:
                    new_cell = _build_cell_xml(ref, value, style=style, sst=sst)
                    xml = _set_cell_in_sheet(xml, ref, new_cell, allow_formula=False)
                    written += 1
            sheet_blobs[path] = xml.encode('utf-8')

        workbook_xml = zin.read('xl/workbook.xml')
        if set_full_calc_on_load:
            workbook_xml = _ensure_full_calc_on_load(workbook_xml)

        modified = {
            **sheet_blobs,
            'xl/sharedStrings.xml': sst.dumps(),
            'xl/workbook.xml': workbook_xml,
        }

        with zipfile.ZipFile(output_path, 'w') as zout:
            for info in zin.infolist():
                data = modified.get(info.filename, zin.read(info.filename))
                # Preserve ZipInfo metadata (date_time, compress_type, extra, flag_bits).
                zout.writestr(info, data)

    return {
        'clearedCells': cleared,
        'writtenInputs': written,
        'patchedSheets': len(sheet_blobs),
        'modifiedParts': sorted(modified.keys()),
    }
