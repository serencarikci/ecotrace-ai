from __future__ import annotations
from typing import Protocol
from ecotrace.shared.infrastructure.prometheus_metrics import collector as _prom

class MetricsCollector(Protocol):

    def increment(self, name: str, *, tags: dict[str, str] | None=None) -> None:
        ...

    def timing(self, name: str, value_ms: float, *, tags: dict[str, str] | None=None) -> None:
        ...

class PrometheusBridge:

    def increment(self, name: str, *, tags: dict[str, str] | None=None) -> None:
        _prom.increment(name, tags=tags)

    def timing(self, name: str, value_ms: float, *, tags: dict[str, str] | None=None) -> None:
        _prom.timing(name, value_ms, tags=tags)
metrics: MetricsCollector = PrometheusBridge()
