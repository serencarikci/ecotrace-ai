"""Official CBAM SEE Excel export (backend).

Status: Phase 12A+ surgical package writer + LibreOffice parity path implemented.
Frontend download UI must NOT start until product acceptance signs off.
"""

from __future__ import annotations

from ecotrace.modules.cbam.application.official_see_export.constants import (
    MAPPING_VERSION,
    TEMPLATE_FILENAME,
    TEMPLATE_SHA256,
)

__all__ = [
    "MAPPING_VERSION",
    "TEMPLATE_FILENAME",
    "TEMPLATE_SHA256",
]
