from __future__ import annotations

from ecotrace.core.exceptions import ConflictError


def check_row_version(current: int, expected: int, *, entity: str) -> None:
    if current != expected:
        raise ConflictError(
            f'{entity} was modified by another request. Reload and retry.',
            details=[{'field': 'rowVersion', 'message': 'Stale row version.'}],
        )
