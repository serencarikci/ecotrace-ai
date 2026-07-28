from __future__ import annotations
import threading
from collections import defaultdict

class PrometheusMetrics:

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._timings_sum: dict[str, float] = defaultdict(float)
        self._timings_count: dict[str, float] = defaultdict(float)

    def increment(self, name: str, *, tags: dict[str, str] | None=None, value: float=1.0) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            self._counters[key] += value

    def timing(self, name: str, value_ms: float, *, tags: dict[str, str] | None=None) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            self._timings_sum[key] += value_ms
            self._timings_count[key] += 1.0

    def gauge(self, name: str, value: float, *, tags: dict[str, str] | None=None) -> None:
        key = _metric_key(name, tags)
        with self._lock:
            self._gauges[key] = value

    def render(self) -> str:
        lines: list[str] = ['# EcoTrace AI metrics']
        with self._lock:
            for key, val in sorted(self._counters.items()):
                lines.append(f'{key} {val}')
            for key, val in sorted(self._gauges.items()):
                lines.append(f'{key} {val}')
            for key, total in sorted(self._timings_sum.items()):
                count = self._timings_count[key] or 1.0
                lines.append(f'{key}_sum {total}')
                lines.append(f'{key}_count {count}')
                lines.append(f'{key}_avg {total / count}')
        return '\n'.join(lines) + '\n'

def _metric_key(name: str, tags: dict[str, str] | None) -> str:
    safe = name.replace('.', '_').replace('-', '_')
    if not tags:
        return safe
    parts = ','.join((f'{k}="{v}"' for k, v in sorted(tags.items())))
    return f'{safe}{ {parts}} '
collector = PrometheusMetrics()

def render_prometheus() -> str:
    return collector.render()
