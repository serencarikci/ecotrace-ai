"""Concurrency / isolation unit tests for Official SEE generation slots."""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from ecotrace.core.exceptions import BusinessRuleError
from ecotrace.modules.cbam.application.official_see_export.concurrency import (
    official_see_org_slot,
)


def test_official_see_org_slot_limits_concurrent_holds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OFFICIAL_SEE_MAX_CONCURRENT_PER_ORG", "1")
    from ecotrace.core.config import reset_settings_cache

    reset_settings_cache()
    org = uuid.uuid4()
    entered = threading.Event()
    release = threading.Event()
    results: list[str] = []

    def holder() -> None:
        with official_see_org_slot(org):
            results.append("held")
            entered.set()
            release.wait(timeout=5)

    def contender() -> None:
        entered.wait(timeout=5)
        try:
            with official_see_org_slot(org):
                results.append("unexpected")
        except BusinessRuleError as exc:
            assert exc.code == "OFFICIAL_SEE_RATE_LIMITED"
            results.append("limited")

    t1 = threading.Thread(target=holder)
    t2 = threading.Thread(target=contender)
    t1.start()
    t2.start()
    assert entered.wait(timeout=5)
    t2.join(timeout=5)
    release.set()
    t1.join(timeout=5)
    assert results.count("held") == 1
    assert results.count("limited") == 1
    # Slot released — a new acquire must succeed.
    with official_see_org_slot(org):
        results.append("reacquired")
    assert "reacquired" in results
    reset_settings_cache()


def test_official_see_org_slot_isolates_tenants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OFFICIAL_SEE_MAX_CONCURRENT_PER_ORG", "1")
    from ecotrace.core.config import reset_settings_cache

    reset_settings_cache()
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    gate = threading.Event()
    done: list[str] = []

    def run(org: uuid.UUID, label: str) -> None:
        with official_see_org_slot(org):
            done.append(label)
            gate.wait(timeout=5)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futs = [
            pool.submit(run, org_a, "a"),
            pool.submit(run, org_b, "b"),
        ]
        # Both tenants should acquire concurrently.
        for _ in range(50):
            if len(done) >= 2:
                break
            threading.Event().wait(0.05)
        assert set(done) == {"a", "b"}
        gate.set()
        for fut in as_completed(futs, timeout=5):
            fut.result()
    reset_settings_cache()
