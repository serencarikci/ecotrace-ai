from __future__ import annotations
from decimal import Decimal
from statistics import mean, pstdev

def z_score(values: list[float], observed: float) -> float | None:
    if len(values) < 2:
        return None
    mu = mean(values)
    sigma = pstdev(values)
    if sigma == 0:
        return 0.0 if observed == mu else float('inf')
    return (observed - mu) / sigma

def iqr_bounds(values: list[float]) -> tuple[float, float] | None:
    if len(values) < 4:
        return None
    ordered = sorted(values)
    n = len(ordered)
    q1 = ordered[n // 4]
    q3 = ordered[3 * n // 4]
    iqr = q3 - q1
    return (q1 - 1.5 * iqr, q3 + 1.5 * iqr)

def percentage_change(previous: float, current: float) -> float | None:
    if previous == 0:
        return None if current == 0 else float('inf')
    return (current - previous) / abs(previous) * 100.0

def is_missing_expected(observed_count: int, expected_count: int) -> bool:
    return observed_count < expected_count

def fingerprint(*parts: object) -> str:
    import hashlib
    raw = '|'.join((str(p) for p in parts))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:48]

def severity_from_score(score: float, mapping: dict[str, float] | None=None) -> str:
    mapping = mapping or {'critical': 4.0, 'high': 3.0, 'medium': 2.0, 'low': 1.0}
    if score >= mapping.get('critical', 4.0):
        return 'critical'
    if score >= mapping.get('high', 3.0):
        return 'high'
    if score >= mapping.get('medium', 2.0):
        return 'medium'
    if score >= mapping.get('low', 1.0):
        return 'low'
    return 'info'

def to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)
