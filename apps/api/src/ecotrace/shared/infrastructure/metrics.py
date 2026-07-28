from __future__ import annotations

from typing import Protocol


class MetricsCollector(Protocol):

    def increment(self, name: str, *, tags: dict[str, str] | None = None) -> None: ...

    def timing(self, name: str, value_ms: float, *, tags: dict[str, str] | None = None) -> None: ...


class NoOpMetrics:

    def increment(self, name: str, *, tags: dict[str, str] | None = None) -> None:
        return None

    def timing(self, name: str, value_ms: float, *, tags: dict[str, str] | None = None) -> None:
        return None


metrics: MetricsCollector = NoOpMetrics()
