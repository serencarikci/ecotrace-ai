from __future__ import annotations
import uuid
from types import SimpleNamespace
import pytest
from ecotrace.core.constants import ROLE_ANALYST, ROLE_SYSTEM_ADMIN
from ecotrace.core.exceptions import AuthorizationError
from ecotrace.modules.identity.application.auth_service import require_roles, user_has_role
from ecotrace.modules.organizations.application.organization_service import user_can_update_organization, user_can_view_organization

def _user(*role_codes: str):
    roles = [SimpleNamespace(code=code) for code in role_codes]
    return SimpleNamespace(id=uuid.uuid4(), roles=roles)

def test_user_has_role() -> None:
    user = _user(ROLE_ANALYST)
    assert user_has_role(user, ROLE_ANALYST)
    assert not user_has_role(user, ROLE_SYSTEM_ADMIN)

def test_require_roles_raises() -> None:
    user = _user(ROLE_ANALYST)
    with pytest.raises(AuthorizationError):
        require_roles(user, ROLE_SYSTEM_ADMIN)

def test_organization_access_rules_system_admin() -> None:
    user = _user(ROLE_SYSTEM_ADMIN)

    class FakeDb:

        def execute(self, *_args, **_kwargs):
            raise AssertionError('system_admin should not query memberships for view')

        def get(self, *_args, **_kwargs):
            return None
    assert user_can_view_organization(FakeDb(), user, uuid.uuid4()) is True
    assert user_can_update_organization(FakeDb(), user, uuid.uuid4()) is True
