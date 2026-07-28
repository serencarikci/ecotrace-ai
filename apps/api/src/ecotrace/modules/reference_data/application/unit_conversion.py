from __future__ import annotations
from decimal import ROUND_HALF_UP, Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from ecotrace.core.exceptions import BusinessRuleError, ValidationAppError
from ecotrace.modules.reference_data.infrastructure.models import ActivityType, Unit

def get_unit(db: Session, code: str) -> Unit:
    unit = db.execute(select(Unit).where(Unit.code == code, Unit.is_active.is_(True))).scalar_one_or_none()
    if unit is None:
        raise ValidationAppError('Unknown or inactive unit.', details=[{'field': 'unitCode', 'message': f"Unit '{code}' is not valid."}])
    return unit

def convert_to_base(quantity: Decimal, unit: Unit) -> Decimal:
    return (quantity * unit.conversion_factor_to_base).quantize(Decimal('0.00000001'), rounding=ROUND_HALF_UP)

def convert_between(quantity: Decimal, source: Unit, target: Unit) -> Decimal:
    if source.dimension != target.dimension:
        raise BusinessRuleError('Cannot convert between different unit dimensions.')
    base = convert_to_base(quantity, source)
    result = base / target.conversion_factor_to_base
    precision = max(0, target.decimal_precision)
    quant = Decimal('1').scaleb(-precision) if precision else Decimal('1')
    return result.quantize(quant, rounding=ROUND_HALF_UP)

def normalize_quantity(db: Session, *, quantity: Decimal, unit_code: str, activity_type: ActivityType) -> tuple[Decimal, str]:
    unit = get_unit(db, unit_code)
    if unit.dimension != activity_type.allowed_unit_dimension:
        raise ValidationAppError('Unit is not compatible with the activity type.', details=[{'field': 'unitCode', 'message': f"Unit dimension '{unit.dimension}' does not match '{activity_type.allowed_unit_dimension}'."}])
    default = get_unit(db, activity_type.default_unit_code)
    normalized = convert_between(quantity, unit, default)
    return (normalized, default.code)
