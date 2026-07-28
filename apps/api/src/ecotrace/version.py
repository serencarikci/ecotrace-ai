from __future__ import annotations

from pathlib import Path

_FALLBACK = "0.3.0"


def _read_version() -> str:
    here = Path(__file__).resolve()
    for candidate in (
        here.parents[2] / "VERSION",
        here.parents[4] / "VERSION",
    ):
        try:
            value = candidate.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if value:
            return value
    return _FALLBACK


__version__ = _read_version()
