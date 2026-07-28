from __future__ import annotations
import pytest
from ecotrace.core.exceptions import ValidationAppError
from ecotrace.modules.activity_data.application.attachment_service import sanitize_original_name

def test_sanitize_strips_path_components() -> None:
    assert sanitize_original_name('../../etc/passwd.pdf') == 'passwd.pdf'
    assert sanitize_original_name('C:\\Windows\\invoice.PDF') == 'invoice.PDF'

def test_sanitize_replaces_unsafe_characters() -> None:
    assert sanitize_original_name('my invoice (final)!.pdf') == 'my_invoice_final_.pdf'

def test_sanitize_rejects_empty_or_dot_names() -> None:
    with pytest.raises(ValidationAppError):
        sanitize_original_name('...')
    with pytest.raises(ValidationAppError):
        sanitize_original_name('../')
