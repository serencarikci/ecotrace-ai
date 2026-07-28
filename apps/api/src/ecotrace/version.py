from __future__ import annotations
from pathlib import Path
_FALLBACK = '0.7.1'

def _read_version() -> str:
    here = Path(__file__).resolve()
    candidates: list[Path] = []
    if len(here.parents) > 2:
        candidates.append(here.parents[2] / 'VERSION')
    if len(here.parents) > 4:
        candidates.append(here.parents[4] / 'VERSION')
    for candidate in candidates:
        try:
            value = candidate.read_text(encoding='utf-8').strip()
        except OSError:
            continue
        if value:
            return value
    return _FALLBACK
__version__ = _read_version()
