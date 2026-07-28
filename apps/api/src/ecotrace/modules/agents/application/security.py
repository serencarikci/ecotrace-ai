from __future__ import annotations
import re
from typing import Any
from ecotrace.core.phase7_constants import PROMPT_INJECTION_MARKERS

def detect_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any((marker in lowered for marker in PROMPT_INJECTION_MARKERS))

def redact_secrets(payload: Any) -> Any:
    if isinstance(payload, dict):
        out: dict[str, Any] = {}
        for key, value in payload.items():
            lk = key.lower()
            if any((s in lk for s in ('password', 'secret', 'token', 'api_key', 'authorization'))):
                out[key] = '[REDACTED]'
            else:
                out[key] = redact_secrets(value)
        return out
    if isinstance(payload, list):
        return [redact_secrets(item) for item in payload]
    if isinstance(payload, str):
        return re.sub('(?i)(bearer\\s+)[a-z0-9\\.\\-_]+', '\\1[REDACTED]', payload)
    return payload
