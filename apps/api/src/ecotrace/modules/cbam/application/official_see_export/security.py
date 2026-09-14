"""Formula-injection safety and download filename helpers."""

from __future__ import annotations

import re
from datetime import date

_FORMULA_INJECTION_PREFIXES = ('=', '+', '-', '@', '\t', '\r', '\n')
_UNSAFE_FILENAME = re.compile(r'[^A-Za-z0-9._-]+')


def excel_safe_text(value: object | None) -> object | None:
    """Prefix risky text with a leading apostrophe so Excel treats it as text."""
    if not isinstance(value, str):
        return value
    if value.startswith(_FORMULA_INJECTION_PREFIXES):
        return f"'{value}"
    return value


def safe_export_filename(
    *,
    installation_name: str,
    period_label: str,
    generated_on: date,
) -> str:
    inst = _UNSAFE_FILENAME.sub('_', installation_name.strip())[:40] or 'installation'
    period = _UNSAFE_FILENAME.sub('_', period_label.strip())[:40] or 'period'
    return f"CBAM_SEE_{inst}_{period}_{generated_on.isoformat()}.xlsx"


def assert_no_filesystem_path_in_response(payload: dict[str, object]) -> None:
    for key, value in payload.items():
        if isinstance(value, str) and ('/' in value or '\\' in value) and key.lower().endswith(
            ('path', 'filepath', 'abspath')
        ):
            raise ValueError(f'Refusing to expose filesystem path via {key}')
