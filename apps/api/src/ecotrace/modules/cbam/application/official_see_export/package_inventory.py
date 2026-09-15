"""Compare XLSX package parts for preservation (CF, extLst, validations, drawings)."""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


@dataclass(frozen=True, slots=True)
class SheetPackageStats:
    name: str
    path: str
    state: str
    cf_rule_count: int
    ext_lst_count: int
    data_validation_count: int
    formula_count: int
    has_drawing_rel: bool


@dataclass(frozen=True, slots=True)
class PackageInventory:
    part_names: tuple[str, ...]
    part_sha256: dict[str, str]
    sheets: tuple[SheetPackageStats, ...]
    named_range_count: int
    named_ranges: tuple[str, ...]
    total_cf_rule: int
    total_ext_lst: int
    drawing_parts: tuple[str, ...]


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def sheet_name_to_path(workbook_xml: bytes, workbook_rels: bytes) -> dict[str, str]:
    rel_root = ET.fromstring(workbook_rels)
    rid_to_target: dict[str, str] = {}
    for rel in rel_root:
        rid_to_target[rel.attrib["Id"]] = rel.attrib["Target"]

    wb_root = ET.fromstring(workbook_xml)
    mapping: dict[str, str] = {}
    for el in wb_root.iter():
        if _local(el.tag) != "sheet":
            continue
        name = el.attrib.get("name")
        rid = el.attrib.get(f"{{{_REL_NS}}}id")
        if not name or not rid:
            continue
        target = rid_to_target.get(rid)
        if not target:
            continue
        path = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
        mapping[name] = path
    return mapping


def sheet_states(workbook_xml: bytes) -> dict[str, str]:
    wb_root = ET.fromstring(workbook_xml)
    states: dict[str, str] = {}
    for el in wb_root.iter():
        if _local(el.tag) != "sheet":
            continue
        name = el.attrib.get("name")
        if name:
            states[name] = el.attrib.get("state") or "visible"
    return states


def named_ranges(workbook_xml: bytes) -> tuple[str, ...]:
    wb_root = ET.fromstring(workbook_xml)
    names: list[str] = []
    for el in wb_root.iter():
        if _local(el.tag) == "definedName":
            n = el.attrib.get("name")
            if n:
                names.append(n)
    return tuple(sorted(names))


def _sheet_has_drawing_rel(zf: zipfile.ZipFile, sheet_path: str) -> bool:
    # xl/worksheets/sheet13.xml → xl/worksheets/_rels/sheet13.xml.rels
    base = Path(sheet_path).name
    rels_path = f"xl/worksheets/_rels/{base}.rels"
    if rels_path not in zf.namelist():
        return False
    data = zf.read(rels_path).decode("utf-8", errors="ignore")
    return "drawing" in data.lower()


def inventory_package(path: Path) -> PackageInventory:
    with zipfile.ZipFile(path, "r") as zf:
        names = tuple(sorted(zf.namelist()))
        digests = {n: _sha256_bytes(zf.read(n)) for n in names}
        wb = zf.read("xl/workbook.xml")
        rels = zf.read("xl/_rels/workbook.xml.rels")
        name_to_path = sheet_name_to_path(wb, rels)
        states = sheet_states(wb)
        names_def = named_ranges(wb)
        sheets: list[SheetPackageStats] = []
        total_cf = 0
        total_ext = 0
        for sheet_name, sheet_path in sorted(name_to_path.items(), key=lambda x: x[0]):
            raw = zf.read(sheet_path).decode("utf-8", errors="ignore")
            cf = raw.count("cfRule")
            ext = raw.count("extLst")
            dv = raw.count("<dataValidation")
            formulas = len(re.findall(r"<f(?:\s[^>]*)?>", raw))
            total_cf += cf
            total_ext += ext
            sheets.append(
                SheetPackageStats(
                    name=sheet_name,
                    path=sheet_path,
                    state=states.get(sheet_name, "visible"),
                    cf_rule_count=cf,
                    ext_lst_count=ext,
                    data_validation_count=dv,
                    formula_count=formulas,
                    has_drawing_rel=_sheet_has_drawing_rel(zf, sheet_path),
                )
            )
        # Also count workbook/styles extLst in totals
        for part in ("xl/workbook.xml", "xl/styles.xml"):
            if part in zf.namelist():
                total_ext += zf.read(part).decode("utf-8", errors="ignore").count("extLst")
        drawings = tuple(sorted(n for n in names if "/drawings/" in n))
        return PackageInventory(
            part_names=names,
            part_sha256=digests,
            sheets=tuple(sheets),
            named_range_count=len(names_def),
            named_ranges=names_def,
            total_cf_rule=total_cf,
            total_ext_lst=total_ext,
            drawing_parts=drawings,
        )


@dataclass(frozen=True, slots=True)
class PackageDiff:
    missing_parts: tuple[str, ...]
    extra_parts: tuple[str, ...]
    changed_parts: tuple[str, ...]
    cf_rule_drops: tuple[tuple[str, int, int], ...]
    ext_lst_drops: tuple[tuple[str, int, int], ...]
    named_range_count_before: int
    named_range_count_after: int
    sheet_state_mismatches: tuple[tuple[str, str, str], ...]


_DATA_SHEETS = frozenset(
    {
        "A_InstData",
        "B_EmInst",
        "C_Emissions&Energy",
        "D_Processes",
        "E_PurchPrec",
        "Summary_Products",
    }
)


def compare_packages(before: PackageInventory, after: PackageInventory) -> PackageDiff:
    before_set = set(before.part_names)
    after_set = set(after.part_names)
    missing = tuple(sorted(before_set - after_set))
    extra = tuple(sorted(after_set - before_set))
    changed = tuple(
        sorted(
            n
            for n in (before_set & after_set)
            if before.part_sha256.get(n) != after.part_sha256.get(n)
        )
    )
    before_sheets = {s.name: s for s in before.sheets}
    after_sheets = {s.name: s for s in after.sheets}
    cf_drops: list[tuple[str, int, int]] = []
    ext_drops: list[tuple[str, int, int]] = []
    state_mismatches: list[tuple[str, str, str]] = []
    for name, b in before_sheets.items():
        a = after_sheets.get(name)
        if a is None:
            continue
        if name in _DATA_SHEETS or b.cf_rule_count or b.ext_lst_count:
            if a.cf_rule_count < b.cf_rule_count:
                cf_drops.append((name, b.cf_rule_count, a.cf_rule_count))
            if a.ext_lst_count < b.ext_lst_count:
                ext_drops.append((name, b.ext_lst_count, a.ext_lst_count))
        if a.state != b.state:
            state_mismatches.append((name, b.state, a.state))
    return PackageDiff(
        missing_parts=missing,
        extra_parts=extra,
        changed_parts=changed,
        cf_rule_drops=tuple(cf_drops),
        ext_lst_drops=tuple(ext_drops),
        named_range_count_before=before.named_range_count,
        named_range_count_after=after.named_range_count,
        sheet_state_mismatches=tuple(state_mismatches),
    )


def assert_critical_markers_preserved(before: PackageInventory, after: PackageInventory) -> None:
    """Raise AssertionError if CF/extLst dropped on data sheets or named ranges lost."""
    diff = compare_packages(before, after)
    if diff.missing_parts:
        raise AssertionError(f"Package parts missing: {diff.missing_parts[:20]}")
    if diff.cf_rule_drops:
        raise AssertionError(f"cfRule count dropped: {diff.cf_rule_drops}")
    if diff.ext_lst_drops:
        raise AssertionError(f"extLst count dropped: {diff.ext_lst_drops}")
    if diff.named_range_count_after < diff.named_range_count_before:
        raise AssertionError(
            f"Named ranges dropped: {diff.named_range_count_before} → {diff.named_range_count_after}"
        )
    if diff.sheet_state_mismatches:
        raise AssertionError(f"Sheet states changed: {diff.sheet_state_mismatches}")
    before_draw = set(before.drawing_parts)
    after_draw = set(after.drawing_parts)
    if before_draw - after_draw:
        raise AssertionError(f"Drawing parts missing: {sorted(before_draw - after_draw)[:20]}")


# LibreOffice may drop or regenerate these parts after convert; exact names/prefixes.
LO_REGENERATED_OR_OPTIONAL_PARTS: tuple[str, ...] = (
    "xl/calcChain.xml",
    "xl/printerSettings/",
    "xl/printerSettings.bin",
    "xl/worksheets/_rels/",
    "docProps/custom.xml",
    "xl/comments",
    "xl/persons/",
    "xl/drawings/",
)


def part_is_lo_allowlisted(part_name: str) -> bool:
    """True when a missing/extra part vs post-write baseline is an expected LO delta."""
    name = part_name.lstrip("/")
    for allowed in LO_REGENERATED_OR_OPTIONAL_PARTS:
        if allowed.endswith("/"):
            if name.startswith(allowed) or name.startswith(allowed.rstrip("/")):
                return True
            if allowed == "xl/printerSettings/" and name.startswith("xl/printerSettings"):
                return True
        elif name == allowed or name.startswith(allowed):
            return True
    return name.startswith("xl/") and "printerSettings" in name and name.endswith(".bin")


def assert_package_acceptable_after_libreoffice(
    before_write_inventory: PackageInventory,
    after_lo_inventory: PackageInventory,
) -> None:
    """Compare post-surgical-write baseline to post-LibreOffice package.

    Fails when worksheets/formulas/cfRule/extLst on data sheets, data validations,
    named ranges, styles, drawings, or sheet hidden states are unexpectedly lost.
    Allows only ``LO_REGENERATED_OR_OPTIONAL_PARTS`` missing/extra parts.
    """
    before = before_write_inventory
    after = after_lo_inventory
    diff = compare_packages(before, after)

    unexpected_missing = tuple(p for p in diff.missing_parts if not part_is_lo_allowlisted(p))
    unexpected_extra = tuple(p for p in diff.extra_parts if not part_is_lo_allowlisted(p))
    if unexpected_missing:
        raise AssertionError(
            f"Unexpected package parts missing after LibreOffice: {unexpected_missing[:30]}"
        )
    if unexpected_extra:
        raise AssertionError(
            f"Unexpected package parts added after LibreOffice: {unexpected_extra[:30]}"
        )

    before_sheets = {s.name: s for s in before.sheets}
    after_sheets = {s.name: s for s in after.sheets}
    for name, b in before_sheets.items():
        a = after_sheets.get(name)
        if a is None:
            raise AssertionError(f"Worksheet missing after LibreOffice: {name}")
        if a.state != b.state:
            raise AssertionError(f"Sheet state changed for {name}: {b.state} → {a.state}")
        if name in _DATA_SHEETS:
            if a.formula_count < b.formula_count:
                raise AssertionError(
                    f"Formulas dropped on {name}: {b.formula_count} → {a.formula_count}"
                )
            if a.cf_rule_count < b.cf_rule_count:
                raise AssertionError(
                    f"cfRule dropped on {name}: {b.cf_rule_count} → {a.cf_rule_count}"
                )
            if a.ext_lst_count < b.ext_lst_count:
                raise AssertionError(
                    f"extLst dropped on {name}: {b.ext_lst_count} → {a.ext_lst_count}"
                )
            if a.data_validation_count < b.data_validation_count:
                raise AssertionError(
                    f"Data validations dropped on {name}: "
                    f"{b.data_validation_count} → {a.data_validation_count}"
                )
            if b.has_drawing_rel and not a.has_drawing_rel:
                raise AssertionError(f"Drawing relationship lost on {name}")

    if after.named_range_count < before.named_range_count:
        raise AssertionError(
            f"Named ranges dropped after LibreOffice: "
            f"{before.named_range_count} → {after.named_range_count}"
        )
    before_draw = set(before.drawing_parts)
    after_draw = set(after.drawing_parts)
    lost_drawings = before_draw - after_draw
    if lost_drawings:
        raise AssertionError(
            f"Drawing parts missing after LibreOffice: {sorted(lost_drawings)[:20]}"
        )

    # styles.xml must remain present
    if "xl/styles.xml" in before.part_names and "xl/styles.xml" not in after.part_names:
        raise AssertionError("xl/styles.xml missing after LibreOffice")
