from __future__ import annotations
from decimal import Decimal
from types import SimpleNamespace
import pytest
from ecotrace.core.exceptions import BusinessRuleError, ValidationAppError
from ecotrace.modules.reference_data.application.unit_conversion import convert_between, convert_to_base, normalize_quantity

def _unit(*, code: str, dimension: str, factor: str, precision: int=4) -> SimpleNamespace:
    return SimpleNamespace(code=code, dimension=dimension, conversion_factor_to_base=Decimal(factor), decimal_precision=precision, is_active=True)

def test_convert_to_base_uses_decimal() -> None:
    mwh = _unit(code='MWh', dimension='energy', factor='1000')
    result = convert_to_base(Decimal('2.5'), mwh)
    assert result == Decimal('2500.00000000')

def test_convert_between_same_dimension() -> None:
    kwh = _unit(code='kWh', dimension='energy', factor='1')
    mwh = _unit(code='MWh', dimension='energy', factor='1000', precision=6)
    result = convert_between(Decimal('1500'), kwh, mwh)
    assert result == Decimal('1.500000')

def test_convert_between_rejects_dimension_mismatch() -> None:
    kwh = _unit(code='kWh', dimension='energy', factor='1')
    kg = _unit(code='kg', dimension='mass', factor='1')
    with pytest.raises(BusinessRuleError):
        convert_between(Decimal('1'), kwh, kg)

def test_normalize_quantity_checks_dimension(seeded_db) -> None:
    from ecotrace.db.seed import seed_activity_types, seed_units
    seed_units(seeded_db)
    types = seed_activity_types(seeded_db)
    activity = types['purchased_electricity']
    with pytest.raises(ValidationAppError):
        normalize_quantity(seeded_db, quantity=Decimal('10'), unit_code='kg', activity_type=activity)

def test_normalize_quantity_mwh_to_kwh(seeded_db) -> None:
    from ecotrace.db.seed import seed_activity_types, seed_units
    seed_units(seeded_db)
    types = seed_activity_types(seeded_db)
    qty, unit = normalize_quantity(seeded_db, quantity=Decimal('1.5'), unit_code='MWh', activity_type=types['purchased_electricity'])
    assert unit == 'kWh'
    assert qty == Decimal('1500.0000')
