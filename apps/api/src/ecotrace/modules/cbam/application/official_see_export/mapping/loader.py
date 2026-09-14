"""Load and validate the versioned Official SEE cell-mapping manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.official_see_export.constants import (
    CODE_MAPPING_OR_TEMPLATE_INVALID,
    MAPPING_VERSION,
    TEMPLATE_SHA256,
)

Direction = Literal[
    'INPUT',
    'FORMULA',
    'OUTPUT',
    'CONTROL',
    'PRESERVE',
    'CLEAR_EXAMPLE',
]

_ALLOWED_DIRECTIONS = frozenset(
    {'INPUT', 'FORMULA', 'OUTPUT', 'CONTROL', 'PRESERVE', 'CLEAR_EXAMPLE'}
)


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    semantic_field: str
    source: str
    sheet: str
    cell: str
    direction: Direction
    unit: str | None
    conversion: str | None
    required: bool
    slot_index: int | None
    expected_formula: str | None
    notes: str


@dataclass(frozen=True, slots=True)
class MappingManifest:
    mapping_version: str
    template_filename: str
    template_sha256: str
    template_version: str
    capacities: dict[str, int]
    entries: tuple[ManifestEntry, ...]
    unsupported_scope: tuple[str, ...]

    def by_direction(self, direction: Direction) -> list[ManifestEntry]:
        return [e for e in self.entries if e.direction == direction]

    def formula_entries(self) -> list[ManifestEntry]:
        return [
            e
            for e in self.entries
            if e.direction in {'FORMULA', 'OUTPUT'} and e.expected_formula
        ]


def manifest_path() -> Path:
    return Path(__file__).resolve().parent / 'manifest_v1.json'


def steel_patch_path() -> Path:
    return Path(__file__).resolve().parent / 'manifest_steel_patch_v1.json'


def process_f_patch_path() -> Path:
    return Path(__file__).resolve().parent / 'manifest_process_f_patch_v1.json'


def _parse_entry(raw: dict[str, Any]) -> ManifestEntry:
    direction = str(raw.get('direction') or '')
    if direction not in _ALLOWED_DIRECTIONS:
        raise BusinessRuleError(
            'Invalid mapping entry direction.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID, 'direction': direction}],
        )
    cell = str(raw.get('cell') or '')
    sheet = str(raw.get('sheet') or '')
    if not cell or not sheet:
        raise BusinessRuleError(
            'Mapping entry missing sheet/cell.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID}],
        )
    slot = raw.get('slot_index')
    return ManifestEntry(
        semantic_field=str(raw.get('semantic_field') or ''),
        source=str(raw.get('source') or ''),
        sheet=sheet,
        cell=cell,
        direction=direction,  # type: ignore[arg-type]
        unit=raw.get('unit'),
        conversion=raw.get('conversion'),
        required=bool(raw.get('required', False)),
        slot_index=int(slot) if slot is not None else None,
        expected_formula=raw.get('expected_formula'),
        notes=str(raw.get('notes') or ''),
    )


def _merge_patch_entries(
    base: list[dict[str, Any]],
    patch_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge patch entries by (sheet, cell, direction), replacing duplicates."""
    index: dict[tuple[str, str, str], int] = {}
    merged: list[dict[str, Any]] = []
    for raw in base:
        key = (str(raw.get('sheet')), str(raw.get('cell')), str(raw.get('direction')))
        index[key] = len(merged)
        merged.append(raw)
    for raw in patch_entries:
        key = (str(raw.get('sheet')), str(raw.get('cell')), str(raw.get('direction')))
        if key in index:
            merged[index[key]] = raw
        else:
            index[key] = len(merged)
            merged.append(raw)
    return merged


@lru_cache(maxsize=1)
def load_manifest() -> MappingManifest:
    path = manifest_path()
    if not path.is_file():
        raise BusinessRuleError(
            'Official SEE mapping manifest missing.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID, 'path': str(path)}],
        )
    payload = json.loads(path.read_text(encoding='utf-8'))
    mapping_version = str(payload.get('mapping_version') or '')
    template_sha = str(payload.get('template_sha256') or '')
    if mapping_version != MAPPING_VERSION:
        raise BusinessRuleError(
            'Official SEE mapping version mismatch.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[
                {
                    'code': CODE_MAPPING_OR_TEMPLATE_INVALID,
                    'expected': MAPPING_VERSION,
                    'actual': mapping_version,
                }
            ],
        )
    if template_sha != TEMPLATE_SHA256:
        raise BusinessRuleError(
            'Official SEE mapping template hash mismatch.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID}],
        )
    raw_entries: list[dict[str, Any]] = list(payload.get('entries') or [])
    for patch in (steel_patch_path(), process_f_patch_path()):
        if not patch.is_file():
            continue
        patch_payload = json.loads(patch.read_text(encoding='utf-8'))
        patch_version = str(patch_payload.get('mapping_version') or mapping_version)
        if patch_version != mapping_version:
            raise BusinessRuleError(
                f'Official SEE patch mapping version mismatch ({patch.name}).',
                code=CODE_MAPPING_OR_TEMPLATE_INVALID,
                details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID}],
            )
        raw_entries = _merge_patch_entries(
            raw_entries, list(patch_payload.get('entries') or [])
        )
    entries = tuple(_parse_entry(e) for e in raw_entries)
    if not entries:
        raise BusinessRuleError(
            'Official SEE mapping has no entries.',
            code=CODE_MAPPING_OR_TEMPLATE_INVALID,
            details=[{'code': CODE_MAPPING_OR_TEMPLATE_INVALID}],
        )
    return MappingManifest(
        mapping_version=mapping_version,
        template_filename=str(payload.get('template_filename') or ''),
        template_sha256=template_sha,
        template_version=str(payload.get('template_version') or ''),
        capacities=dict(payload.get('capacities') or {}),
        entries=entries,
        unsupported_scope=tuple(payload.get('unsupported_scope') or ()),
    )


def validate_manifest_or_raise() -> MappingManifest:
    return load_manifest()
