from __future__ import annotations
import math
from decimal import Decimal

def mae(actual: list[float], predicted: list[float]) -> float:
    n = min(len(actual), len(predicted))
    if n == 0:
        return 0.0
    return sum((abs(actual[i] - predicted[i]) for i in range(n))) / n

def rmse(actual: list[float], predicted: list[float]) -> float:
    n = min(len(actual), len(predicted))
    if n == 0:
        return 0.0
    return math.sqrt(sum(((actual[i] - predicted[i]) ** 2 for i in range(n))) / n)

def mape(actual: list[float], predicted: list[float]) -> float | None:
    pairs = [(a, p) for a, p in zip(actual, predicted, strict=False) if a != 0]
    if not pairs:
        return None
    return sum((abs((a - p) / a) for a, p in pairs)) / len(pairs) * 100.0

def smape(actual: list[float], predicted: list[float]) -> float | None:
    n = min(len(actual), len(predicted))
    if n == 0:
        return None
    total = 0.0
    count = 0
    for i in range(n):
        denom = abs(actual[i]) + abs(predicted[i])
        if denom == 0:
            continue
        total += abs(actual[i] - predicted[i]) / (denom / 2.0)
        count += 1
    if count == 0:
        return None
    return total / count * 100.0

def linear_trend(values: list[float], horizon: int) -> list[float]:
    n = len(values)
    if n < 2:
        return [values[-1] if values else 0.0] * horizon
    xs = list(range(n))
    x_mean = sum(xs) / n
    y_mean = sum(values) / n
    num = sum(((x - x_mean) * (y - y_mean) for x, y in zip(xs, values, strict=True)))
    den = sum(((x - x_mean) ** 2 for x in xs)) or 1.0
    slope = num / den
    intercept = y_mean - slope * x_mean
    return [intercept + slope * (n + i) for i in range(horizon)]

def moving_average(values: list[float], horizon: int, window: int=3) -> list[float]:
    if not values:
        return [0.0] * horizon
    w = min(window, len(values))
    avg = sum(values[-w:]) / w
    return [avg for _ in range(horizon)]

def weighted_moving_average(values: list[float], horizon: int, window: int=3) -> list[float]:
    if not values:
        return [0.0] * horizon
    w = min(window, len(values))
    weights = list(range(1, w + 1))
    chunk = values[-w:]
    avg = sum((v * wt for v, wt in zip(chunk, weights, strict=True))) / sum(weights)
    return [avg for _ in range(horizon)]

def seasonal_naive(values: list[float], horizon: int, season: int=12) -> list[float]:
    if not values:
        return [0.0] * horizon
    out: list[float] = []
    for i in range(horizon):
        idx = len(values) - season + i % season
        if idx < 0:
            out.append(values[-1])
        else:
            out.append(values[idx])
    return out

def simple_exponential_smoothing(values: list[float], horizon: int, alpha: float=0.3) -> list[float]:
    if not values:
        return [0.0] * horizon
    level = values[0]
    for v in values[1:]:
        level = alpha * v + (1 - alpha) * level
    return [level for _ in range(horizon)]

def holt_linear(values: list[float], horizon: int, alpha: float=0.3, beta: float=0.1) -> list[float]:
    if len(values) < 2:
        return moving_average(values, horizon)
    level = values[0]
    trend = values[1] - values[0]
    for v in values[1:]:
        prev_level = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend
    return [level + (i + 1) * trend for i in range(horizon)]

def select_method(values: list[float], horizon: int=3) -> str:
    if len(values) < 6:
        return 'moving_average'
    hold = min(3, len(values) // 4 or 1)
    train = values[:-hold]
    actual = values[-hold:]
    candidates = {'linear_trend': linear_trend(train, hold), 'moving_average': moving_average(train, hold), 'weighted_moving_average': weighted_moving_average(train, hold), 'seasonal_naive': seasonal_naive(train, hold, season=min(12, len(train))), 'simple_exponential_smoothing': simple_exponential_smoothing(train, hold), 'holt_linear': holt_linear(train, hold)}
    best = min(candidates.items(), key=lambda item: mae(actual, item[1]))
    _ = horizon
    return best[0]

def run_method(method: str, values: list[float], horizon: int) -> list[float]:
    mapping = {'linear_trend': linear_trend, 'moving_average': moving_average, 'weighted_moving_average': weighted_moving_average, 'seasonal_naive': seasonal_naive, 'simple_exponential_smoothing': simple_exponential_smoothing, 'holt_linear': holt_linear}
    fn = mapping.get(method, moving_average)
    return fn(values, horizon)

def accuracy_bundle(actual: list[float], predicted: list[float]) -> dict[str, float | None]:
    return {'mae': mae(actual, predicted), 'rmse': rmse(actual, predicted), 'mape': mape(actual, predicted), 'smape': smape(actual, predicted)}

def d(value: float) -> Decimal:
    return Decimal(str(round(value, 8)))

def target_trajectory_label(*, current: float, target: float, forecast_at_target: float | None, periods_remaining: int) -> str:
    if periods_remaining <= 0 or forecast_at_target is None:
        return 'insufficient_data'
    gap = forecast_at_target - target
    if target <= current:
        if forecast_at_target <= target:
            return 'likely_on_track'
        if forecast_at_target <= current:
            return 'potentially_at_risk'
        return 'likely_off_track'
    if forecast_at_target >= target:
        return 'likely_on_track'
    if gap > 0:
        return 'potentially_at_risk'
    return 'likely_off_track'
