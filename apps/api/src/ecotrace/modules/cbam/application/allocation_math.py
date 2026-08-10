from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ecotrace.core.exceptions import ValidationAppError

QUANTITY_SCALE = Decimal('0.00000001')
RATIO_SCALE = Decimal('0.000000000001')
CALCULATION_VERSION = 'allocation-quantity-v1'

ALLOCATION_METHODS = frozenset(
    {'DIRECT_ASSIGNMENT', 'PRODUCTION_QUANTITY_RATIO', 'MANUAL_RATIO'}
)


def quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_SCALE, rounding=ROUND_HALF_UP)


def quantize_ratio(value: Decimal) -> Decimal:
    return value.quantize(RATIO_SCALE, rounding=ROUND_HALF_UP)


def compute_allocated_quantity(*, source_quantity: Decimal, allocation_ratio: Decimal) -> Decimal:
    return quantize_quantity(source_quantity * allocation_ratio)


def direct_assignment_ratio() -> Decimal:
    return Decimal('1')


def validate_manual_ratio(ratio: Decimal) -> Decimal:
    if ratio < 0 or ratio > 1:
        raise ValidationAppError(
            'Manual allocation ratio must be between 0 and 1 inclusive.',
            details=[{'field': 'allocationRatio', 'message': 'Must be in [0, 1].'}],
        )
    return quantize_ratio(ratio)


def compute_production_quantity_ratio(
    *,
    numerator: Decimal,
    denominator: Decimal,
) -> Decimal:
    if denominator <= 0:
        raise ValidationAppError(
            'Allocation-base production quantity (denominator) must be greater than zero.',
            details=[{'field': 'denominatorProductionRecordId', 'message': 'Denominator must be > 0.'}],
        )
    if numerator < 0:
        raise ValidationAppError(
            'Target production quantity (numerator) cannot be negative.',
            details=[{'field': 'numeratorProductionRecordId', 'message': 'Numerator must be >= 0.'}],
        )
    if numerator > denominator:
        raise ValidationAppError(
            'Target production quantity cannot exceed allocation-base production quantity.',
            details=[
                {
                    'field': 'numeratorProductionRecordId',
                    'message': 'Numerator must be <= denominator.',
                }
            ],
        )
    return quantize_ratio(numerator / denominator)
