"""In-process concurrency guard for expensive Official SEE generation."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from ecotrace.core.config import get_settings
from ecotrace.core.exceptions import BusinessRuleError

_lock = threading.Lock()
_active: dict[str, int] = {}


@contextmanager
def official_see_org_slot(organization_id: uuid.UUID) -> Iterator[None]:
    """Limit concurrent Official SEE runs per organization (fail closed)."""
    settings = get_settings()
    limit = settings.official_see_max_concurrent_per_org
    key = str(organization_id)
    with _lock:
        current = _active.get(key, 0)
        if current >= limit:
            raise BusinessRuleError(
                "Too many Official Excel generations in progress for this organization. Try again shortly.",
                code="OFFICIAL_SEE_RATE_LIMITED",
                details=[{"code": "OFFICIAL_SEE_RATE_LIMITED"}],
            )
        _active[key] = current + 1
    try:
        yield
    finally:
        with _lock:
            remaining = _active.get(key, 1) - 1
            if remaining <= 0:
                _active.pop(key, None)
            else:
                _active[key] = remaining
