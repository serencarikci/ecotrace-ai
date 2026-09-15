"""Authoritative product-field applicability for CN codes (Phase 6A+)."""

from __future__ import annotations

from typing import Any

from ecotrace.shared.domain.schemas import CamelModel

FIELD_APPLICABILITY_KEYS = (
    "reducingAgent",
    "steelMillIdentificationNumber",
    "percentMn",
    "percentCr",
    "percentNi",
    "percentOtherAlloys",
    "percentOtherMaterials",
)

# API camelCase key → ORM attribute on CbamProductProfileVersion
FIELD_ATTR_BY_KEY = {
    "reducingAgent": "reducing_agent",
    "steelMillIdentificationNumber": "steel_mill_identification_number",
    "percentMn": "percent_mn",
    "percentCr": "percent_cr",
    "percentNi": "percent_ni",
    "percentOtherAlloys": "percent_other_alloys",
    "percentOtherMaterials": "percent_other_materials",
}

# Request/model snake_case → API camelCase key
KEY_BY_ATTR = {attr: key for key, attr in FIELD_ATTR_BY_KEY.items()}

PERCENT_KEY_BY_ATTR = {
    "percent_mn": "percentMn",
    "percent_cr": "percentCr",
    "percent_ni": "percentNi",
    "percent_other_alloys": "percentOtherAlloys",
    "percent_other_materials": "percentOtherMaterials",
}


class FieldApplicability(CamelModel):
    """Stable camelCase applicability contract (all keys always present)."""

    reducing_agent: bool = False
    steel_mill_identification_number: bool = False
    percent_mn: bool = False
    percent_cr: bool = False
    percent_ni: bool = False
    percent_other_alloys: bool = False
    percent_other_materials: bool = False

    @classmethod
    def from_raw(cls, raw: Any) -> FieldApplicability:
        normalized = normalize_field_applicability(raw)
        return cls(
            reducing_agent=normalized["reducingAgent"],
            steel_mill_identification_number=normalized["steelMillIdentificationNumber"],
            percent_mn=normalized["percentMn"],
            percent_cr=normalized["percentCr"],
            percent_ni=normalized["percentNi"],
            percent_other_alloys=normalized["percentOtherAlloys"],
            percent_other_materials=normalized["percentOtherMaterials"],
        )


def empty_field_applicability() -> dict[str, bool]:
    return {key: False for key in FIELD_APPLICABILITY_KEYS}


def normalize_field_applicability(raw: Any) -> dict[str, bool]:
    """Ensure all contract keys are present as booleans."""
    source = raw if isinstance(raw, dict) else {}
    # Accept either camelCase seed keys or snake_case ORM dump aliases.
    resolved: dict[str, Any] = {}
    for key in FIELD_APPLICABILITY_KEYS:
        if key in source:
            resolved[key] = source[key]
        else:
            snake = FIELD_ATTR_BY_KEY[key]
            if snake in source:
                resolved[key] = source[snake]
    return {key: bool(resolved.get(key, False)) for key in FIELD_APPLICABILITY_KEYS}


def field_applicability_from_sector_entry(entry: dict[str, Any] | None) -> dict[str, bool]:
    """Map workbook-derived sectorSpecialParameters entry → API contract keys."""
    if not entry:
        return empty_field_applicability()
    raw_flags = entry.get("flags")
    flags: dict[str, Any] = raw_flags if isinstance(raw_flags, dict) else {}
    return normalize_field_applicability(
        {
            "reducingAgent": flags.get("reducingAgent", False),
            "steelMillIdentificationNumber": flags.get("steelMillIdentificationNumber", False),
            "percentMn": flags.get("percentMn", False),
            "percentCr": flags.get("percentCr", False),
            "percentNi": flags.get("percentNi", False),
            "percentOtherAlloys": flags.get("percentOtherAlloys", False),
            "percentOtherMaterials": entry.get("percentOtherMaterials", False),
        }
    )


def field_applicability_from_cn_payload(
    *,
    sector: str,
    sector_special_parameters: dict[str, Any],
    explicit: dict[str, Any] | None = None,
) -> dict[str, bool]:
    if explicit is not None:
        return normalize_field_applicability(explicit)
    entry = sector_special_parameters.get(sector)
    return field_applicability_from_sector_entry(entry if isinstance(entry, dict) else None)


def field_applicability_for_cn(cn: Any | None) -> dict[str, bool]:
    """Read persisted CN-row applicability (authoritative); never sector-name matching."""
    if cn is None:
        return empty_field_applicability()
    raw = getattr(cn, "field_applicability", None)
    return normalize_field_applicability(raw)


def clear_non_applicable_special_fields(row: Any, applicability: dict[str, bool]) -> None:
    """Null out special fields that are not applicable to the selected CN (draft CN change)."""
    fa = normalize_field_applicability(applicability)
    for key, attr in FIELD_ATTR_BY_KEY.items():
        if not fa[key]:
            setattr(row, attr, None)


def collect_non_applicable_write_errors(
    applicability: dict[str, bool],
    *,
    explicit_attrs: dict[str, Any],
) -> list[dict[str, str]]:
    """Fail-closed errors when the client sets a non-applicable field to a non-null value."""
    fa = normalize_field_applicability(applicability)
    errors: list[dict[str, str]] = []
    for attr, value in explicit_attrs.items():
        key = KEY_BY_ATTR.get(attr)
        if key is None:
            continue
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if not fa[key]:
            errors.append(
                {
                    "code": f"{attr.upper()}_NOT_APPLICABLE",
                    "field": key,
                    "message": (
                        "This field is not applicable to the selected CN code "
                        "and cannot be persisted."
                    ),
                }
            )
    return errors
