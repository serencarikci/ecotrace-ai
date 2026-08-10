from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from ecotrace.core.exceptions import ValidationAppError
from ecotrace.shared.domain.schemas import CamelModel

ACTIVITY_GROUPS: Final[tuple[str, ...]] = (
    'DIRECT',
    'PURCHASED_ENERGY',
    'PROCESS',
    'OTHER',
)

DATA_SOURCE_TYPES: Final[tuple[str, ...]] = (
    'PRIMARY',
    'DEFAULT_REFERENCE',
    'UNKNOWN',
)

RECORD_SOURCE_TYPES: Final[tuple[str, ...]] = ('MANUAL', 'IMPORTED')

BIOGENIC_STATUSES: Final[tuple[str, ...]] = (
    'BIOGENIC',
    'NON_BIOGENIC',
    'UNKNOWN',
)

EMBEDDED_EMISSION_SOURCE_TYPES: Final[tuple[str, ...]] = (
    'PRIMARY',
    'DEFAULT_REFERENCE',
    'UNKNOWN',
    'NOT_PROVIDED',
)

UNIT_FAMILIES: Final[tuple[str, ...]] = ('energy', 'volume', 'mass', 'count')

RECORD_STATUSES: Final[tuple[str, ...]] = ('active', 'archived')

PROCESS_TYPE_CODES: Final[tuple[str, ...]] = ('OTHER_PROCESS',)

ACTIVITY_PROPERTY_CODES: Final[tuple[str, ...]] = (
    'NET_CALORIFIC_VALUE',
    'GROSS_CALORIFIC_VALUE',
)


@dataclass(frozen=True, slots=True)
class UnitDef:
    code: str
    display_name: str
    family: str


@dataclass(frozen=True, slots=True)
class ActivityTypeDef:
    code: str
    display_name: str
    activity_group: str
    allowed_unit_family: str


UNITS: Final[tuple[UnitDef, ...]] = (
    UnitDef('kWh', 'Kilowatt-hour', 'energy'),
    UnitDef('MWh', 'Megawatt-hour', 'energy'),
    UnitDef('GJ', 'Gigajoule', 'energy'),
    UnitDef('MJ', 'Megajoule', 'energy'),
    UnitDef('L', 'Litre', 'volume'),
    UnitDef('m3', 'Cubic metre', 'volume'),
    UnitDef('kg', 'Kilogram', 'mass'),
    UnitDef('t', 'Tonne', 'mass'),
    UnitDef('unit', 'Unit count', 'count'),
)

PROPERTY_UNITS: Final[tuple[UnitDef, ...]] = (
    UnitDef('MJ/L', 'Megajoule per litre', 'energy_per_volume'),
    UnitDef('GJ/t', 'Gigajoule per tonne', 'energy_per_mass'),
    UnitDef('MJ/kg', 'Megajoule per kilogram', 'energy_per_mass'),
    UnitDef('GJ/m3', 'Gigajoule per cubic metre', 'energy_per_volume'),
    UnitDef('MJ/m3', 'Megajoule per cubic metre', 'energy_per_volume'),
    UnitDef('tCO2e/t', 'Declared embedded emission intensity', 'embedded_intensity'),
)

ACTIVITY_TYPES: Final[tuple[ActivityTypeDef, ...]] = (
    ActivityTypeDef('ELECTRICITY', 'Electricity', 'PURCHASED_ENERGY', 'energy'),
    ActivityTypeDef('NATURAL_GAS', 'Natural gas', 'PURCHASED_ENERGY', 'volume'),
    ActivityTypeDef('DIESEL', 'Diesel', 'DIRECT', 'volume'),
    ActivityTypeDef('GASOLINE', 'Gasoline', 'DIRECT', 'volume'),
    ActivityTypeDef('LPG', 'LPG', 'DIRECT', 'mass'),
    ActivityTypeDef('PURCHASED_STEAM', 'Purchased steam', 'PURCHASED_ENERGY', 'energy'),
    ActivityTypeDef('PROCESS_ACTIVITY', 'Process activity', 'PROCESS', 'mass'),
    ActivityTypeDef('OTHER_FUEL', 'Other fuel', 'DIRECT', 'volume'),
    ActivityTypeDef('OTHER', 'Other activity', 'OTHER', 'mass'),
)

_UNITS_BY_CODE: Final[dict[str, UnitDef]] = {u.code: u for u in UNITS}
_PROPERTY_UNITS_BY_CODE: Final[dict[str, UnitDef]] = {u.code: u for u in PROPERTY_UNITS}
_ACTIVITY_BY_CODE: Final[dict[str, ActivityTypeDef]] = {a.code: a for a in ACTIVITY_TYPES}

_SCALE_TO_CANONICAL: Final[dict[str, tuple[str, Decimal]]] = {
    'MJ': ('J_canon', Decimal('1e6')),
    'GJ': ('J_canon', Decimal('1e9')),
    'kWh': ('Wh_canon', Decimal('1000')),
    'MWh': ('Wh_canon', Decimal('1000000')),
    'kg': ('kg_canon', Decimal('1')),
    't': ('kg_canon', Decimal('1000')),
}

EMISSION_INTENSITY_UNITS: Final[tuple[str, ...]] = (
    'kgCO2e/kWh',
    'kgCO2e/MWh',
    'tCO2e/kWh',
    'tCO2e/MWh',
    'kgCO2/kWh',
    'kgCO2/MWh',
    'tCO2/kWh',
    'tCO2/MWh',
    'kgCO2e/L',
    'kgCO2/L',
    'tCO2e/t',
    'tCO2/t',
    'kgCO2e/t',
    'kgCO2e/kg',
    'kgCO2/kg',
    'tCO2e/kg',
)


def get_property_unit(code: str) -> UnitDef | None:
    return _PROPERTY_UNITS_BY_CODE.get(code) or _UNITS_BY_CODE.get(code)


def is_known_factor_unit(code: str) -> bool:
    return get_property_unit(code) is not None or code in EMISSION_INTENSITY_UNITS


def get_emission_intensity_parts(factor_unit: str) -> tuple[str, str] | None:
    if factor_unit not in EMISSION_INTENSITY_UNITS:
        return None
    if '/' not in factor_unit:
        return None
    result_unit, per_unit = factor_unit.split('/', 1)
    if not result_unit or not per_unit:
        return None
    return result_unit, per_unit


def convert_to_canonical(quantity: Decimal, unit: str) -> Decimal | None:
    if unit not in _SCALE_TO_CANONICAL:
        if get_unit(unit) is not None:
            return quantity
        return None
    _family, scale = _SCALE_TO_CANONICAL[unit]
    return quantity * scale


def units_exactly_compatible(unit_a: str, unit_b: str) -> bool:
    if unit_a == unit_b:
        return True
    a = _SCALE_TO_CANONICAL.get(unit_a)
    b = _SCALE_TO_CANONICAL.get(unit_b)
    return a is not None and b is not None and a[0] == b[0]


class UnitResponse(CamelModel):
    code: str
    display_name: str
    family: str


class ActivityTypeResponse(CamelModel):
    code: str
    display_name: str
    activity_group: str
    allowed_unit_family: str


class ActivityPropertyTypeResponse(CamelModel):
    code: str
    display_name: str


def get_unit(code: str) -> UnitDef | None:
    return _UNITS_BY_CODE.get(code)


def require_unit(code: str) -> str:
    normalized = code.strip()
    if get_unit(normalized) is None:
        raise ValidationAppError(f'Unsupported unit: {normalized}')
    return normalized


def get_activity_type(code: str) -> ActivityTypeDef | None:
    return _ACTIVITY_BY_CODE.get(code)


def list_unit_responses() -> list[UnitResponse]:
    return [
        UnitResponse(code=u.code, display_name=u.display_name, family=u.family) for u in UNITS
    ]


def list_activity_type_responses() -> list[ActivityTypeResponse]:
    return [
        ActivityTypeResponse(
            code=a.code,
            display_name=a.display_name,
            activity_group=a.activity_group,
            allowed_unit_family=a.allowed_unit_family,
        )
        for a in ACTIVITY_TYPES
    ]


def list_activity_property_type_responses() -> list[ActivityPropertyTypeResponse]:
    labels = {
        'NET_CALORIFIC_VALUE': 'Net calorific value',
        'GROSS_CALORIFIC_VALUE': 'Gross calorific value',
    }
    return [
        ActivityPropertyTypeResponse(code=code, display_name=labels[code])
        for code in ACTIVITY_PROPERTY_CODES
    ]


def unit_compatible(unit_code: str, family: str) -> bool:
    unit = get_unit(unit_code)
    return unit is not None and unit.family == family


def same_unit_family(unit_a: str, unit_b: str) -> bool:
    a = get_unit(unit_a)
    b = get_unit(unit_b)
    return a is not None and b is not None and a.family == b.family and a.code == b.code
