from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ecotrace.core.constants import (
    ROLE_ANALYST,
    ROLE_ORGANIZATION_ADMIN,
    ROLE_SYSTEM_ADMIN,
    ROLE_VIEWER,
)
from ecotrace.core.exceptions import AuthorizationError, NotFoundError
from ecotrace.modules.cbam.application import permissions as cbam_permissions
from ecotrace.modules.cbam.application.permissions import (
    CBAM_APPROVE,
    CBAM_CALCULATE,
    CBAM_PERMISSION_ROLE_MAP,
    CBAM_PERMISSION_VOCABULARY,
    CBAM_VIEW,
    require_cbam_approve,
    require_cbam_permission,
    require_cbam_view,
)


def _user(*role_codes: str):
    roles = [SimpleNamespace(code=code) for code in role_codes]
    return SimpleNamespace(id=uuid.uuid4(), roles=roles)


def test_permission_vocabulary_contains_expected_capabilities() -> None:
    expected = {
        "cbam:view",
        "cbam:configure",
        "cbam:data:write",
        "cbam:data:review",
        "cbam:calculate",
        "cbam:approve",
        "cbam:lock",
        "cbam:report",
        "cbam:evidence:view",
        "cbam:evidence:write",
        "cbam:audit:view",
    }
    assert set(CBAM_PERMISSION_VOCABULARY) == expected
    assert set(CBAM_PERMISSION_ROLE_MAP) == expected
    assert ROLE_VIEWER in CBAM_PERMISSION_ROLE_MAP[CBAM_VIEW]
    assert ROLE_VIEWER not in CBAM_PERMISSION_ROLE_MAP[CBAM_APPROVE]
    assert ROLE_ANALYST in CBAM_PERMISSION_ROLE_MAP[CBAM_CALCULATE]
    assert ROLE_ORGANIZATION_ADMIN in CBAM_PERMISSION_ROLE_MAP[CBAM_APPROVE]


def test_require_cbam_view_system_admin_bypasses_membership_query() -> None:
    user = _user(ROLE_SYSTEM_ADMIN)
    db = MagicMock()
    codes = require_cbam_view(db, user, uuid.uuid4())  # type: ignore[arg-type]
    assert ROLE_SYSTEM_ADMIN in codes
    db.execute.assert_not_called()


def test_require_cbam_permission_unknown_raises() -> None:
    user = _user(ROLE_ANALYST)
    with pytest.raises(ValueError, match="Unknown CBAM permission"):
        require_cbam_permission(MagicMock(), user, uuid.uuid4(), "cbam:unknown")  # type: ignore[arg-type]


def test_require_cbam_approve_rejects_insufficient_role(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _user(ROLE_VIEWER)
    monkeypatch.setattr(
        cbam_permissions,
        "require_org_roles",
        lambda *_a, **_k: (_ for _ in ()).throw(AuthorizationError()),
    )
    with pytest.raises(AuthorizationError):
        require_cbam_approve(MagicMock(), user, uuid.uuid4())  # type: ignore[arg-type]


def test_require_cbam_view_propagates_not_found_for_non_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _user(ROLE_ANALYST)
    monkeypatch.setattr(
        cbam_permissions,
        "require_org_roles",
        lambda *_a, **_k: (_ for _ in ()).throw(NotFoundError("Organization not found.")),
    )
    with pytest.raises(NotFoundError):
        require_cbam_view(MagicMock(), user, uuid.uuid4())  # type: ignore[arg-type]
