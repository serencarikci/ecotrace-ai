from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from ecotrace.core.constants import ROLE_ORGANIZATION_ADMIN, ROLE_SYSTEM_ADMIN, ROLE_VIEWER
from ecotrace.core.exceptions import AuthorizationError, NotFoundError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application.permissions import (
    CBAM_ENFORCED_PERMISSIONS,
    CBAM_PERMISSION_VOCABULARY,
    CBAM_VIEW,
    require_cbam_configure,
    require_cbam_view,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization


def test_phase2_enforced_permissions_include_view_and_configure() -> None:
    from ecotrace.modules.cbam.application.permissions import CBAM_CONFIGURE

    assert CBAM_ENFORCED_PERMISSIONS == (CBAM_VIEW, CBAM_CONFIGURE)
    assert CBAM_VIEW in CBAM_PERMISSION_VOCABULARY
    assert CBAM_CONFIGURE in CBAM_PERMISSION_VOCABULARY
    assert "cbam:approve" in CBAM_PERMISSION_VOCABULARY


def test_require_cbam_view_allows_viewer_member(seeded_db) -> None:
    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    user = seeded_db.execute(
        select(User).where(User.normalized_email == "viewer@ecotrace.dev")
    ).scalar_one()
    codes = require_cbam_view(seeded_db, user, org.id)
    assert ROLE_VIEWER in codes


def test_require_cbam_view_allows_org_admin_member(seeded_db) -> None:
    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    user = seeded_db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()
    codes = require_cbam_view(seeded_db, user, org.id)
    assert ROLE_ORGANIZATION_ADMIN in codes


def test_require_cbam_view_rejects_non_member_with_not_found(seeded_db) -> None:
    user = seeded_db.execute(
        select(User).where(User.normalized_email == "viewer@ecotrace.dev")
    ).scalar_one()
    other = Organization(
        id=uuid.uuid4(),
        name="CBAM Permission Isolation Org",
        slug="cbam-permission-isolation",
        country_code="US",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(other)
    seeded_db.flush()
    with pytest.raises(NotFoundError):
        require_cbam_view(seeded_db, user, other.id)


def test_require_cbam_view_system_admin_allowed_without_membership_row(seeded_db) -> None:
    admin = seeded_db.execute(
        select(User).where(User.normalized_email == "admin@ecotrace.dev")
    ).scalar_one()
    foreign = Organization(
        id=uuid.uuid4(),
        name="CBAM Admin Access Org",
        slug="cbam-admin-access-org",
        country_code="DE",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(foreign)
    seeded_db.flush()
    codes = require_cbam_view(seeded_db, admin, foreign.id)
    assert ROLE_SYSTEM_ADMIN in codes


def test_require_cbam_configure_allows_org_admin_rejects_viewer(seeded_db) -> None:
    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    viewer = seeded_db.execute(
        select(User).where(User.normalized_email == "viewer@ecotrace.dev")
    ).scalar_one()
    org_admin = seeded_db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()

    require_cbam_view(seeded_db, viewer, org.id)

    with pytest.raises(AuthorizationError) as rejected:
        require_cbam_configure(seeded_db, viewer, org.id)
    assert rejected.value.status_code == 403
    assert rejected.value.code == "AUTHORIZATION_ERROR"

    codes = require_cbam_configure(seeded_db, org_admin, org.id)
    assert ROLE_ORGANIZATION_ADMIN in codes


def test_require_cbam_configure_cross_tenant_returns_not_found(seeded_db) -> None:
    org_admin = seeded_db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()
    other = Organization(
        id=uuid.uuid4(),
        name="CBAM Configure Isolation Org",
        slug="cbam-configure-isolation",
        country_code="US",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(other)
    seeded_db.flush()
    with pytest.raises(NotFoundError):
        require_cbam_configure(seeded_db, org_admin, other.id)
