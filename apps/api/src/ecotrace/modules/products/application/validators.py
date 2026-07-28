from __future__ import annotations
from decimal import Decimal
from ecotrace.core.exceptions import ValidationAppError
from ecotrace.core.lca_constants import DATA_QUALITY_MAX, DATA_QUALITY_MIN, REPAIRABILITY_SCALE_MAX, REPAIRABILITY_SCALE_MIN, SUSTAINABILITY_RATING_MAX, SUSTAINABILITY_RATING_MIN

def require_percentage(value: Decimal | None, field: str) -> None:
    if value is None:
        return
    if value < 0 or value > 100:
        raise ValidationAppError(f'{field} must be between 0 and 100.', details=[{'field': field, 'message': 'Must be between 0 and 100.'}])

def require_non_negative(value: Decimal | None, field: str) -> None:
    if value is None:
        return
    if value < 0:
        raise ValidationAppError(f'{field} must be non-negative.', details=[{'field': field, 'message': 'Must be >= 0.'}])

def require_positive(value: Decimal, field: str) -> None:
    if value <= 0:
        raise ValidationAppError(f'{field} must be positive.', details=[{'field': field, 'message': 'Must be > 0.'}])

def require_repairability(score: int | None) -> None:
    if score is None:
        return
    if score < REPAIRABILITY_SCALE_MIN or score > REPAIRABILITY_SCALE_MAX:
        raise ValidationAppError(f'Repairability score must be {REPAIRABILITY_SCALE_MIN}-{REPAIRABILITY_SCALE_MAX}.', details=[{'field': 'repairabilityScore', 'message': 'Internal scale 1-10.'}])

def require_sustainability_rating(score: int | None) -> None:
    if score is None:
        return
    if score < SUSTAINABILITY_RATING_MIN or score > SUSTAINABILITY_RATING_MAX:
        raise ValidationAppError(f'Sustainability rating must be {SUSTAINABILITY_RATING_MIN}-{SUSTAINABILITY_RATING_MAX}.', details=[{'field': 'sustainabilityRating', 'message': 'Internal indicator 1-5, not certified.'}])

def require_dq_score(score: int, field: str) -> None:
    if score < DATA_QUALITY_MIN or score > DATA_QUALITY_MAX:
        raise ValidationAppError(f'{field} must be {DATA_QUALITY_MIN}-{DATA_QUALITY_MAX}.', details=[{'field': field, 'message': 'Internal data quality indicator 1-5.'}])

def require_allocation_factor(value: Decimal) -> None:
    if value < 0 or value > 1:
        raise ValidationAppError('Allocation factor must be between 0 and 1.', details=[{'field': 'allocationFactor', 'message': 'Must be between 0 and 1.'}])
