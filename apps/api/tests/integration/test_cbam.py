from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from tests.helpers import api_login, auth_headers, current_org_id

from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application.module_status_service import FOUNDATION_MESSAGE
from ecotrace.modules.organizations.infrastructure.models import Organization


def _status_url(org_id: str | uuid.UUID) -> str:
    return f"/api/v1/cbam/organizations/{org_id}/module-status"


def test_cbam_router_registered_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema.get("paths", {})
    assert "/api/v1/cbam/organizations/{organization_id}/module-status" in paths


def test_cbam_module_status_unauthenticated(client: TestClient) -> None:
    response = client.get(_status_url(uuid.uuid4()))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_cbam_module_status_authorized_org_admin(client: TestClient) -> None:
    token = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, token)
    response = client.get(_status_url(org_id), headers=auth_headers(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["module"] == "cbam"
    assert body["uiLabelTr"] == "SKDM"
    assert body["status"] == "foundation_available"
    assert body["foundationAvailable"] is True
    assert body["domainFunctionalityImplemented"] is False
    assert body["complianceClaim"] is False
    assert body["calculationImplemented"] is False
    assert body["message"] == FOUNDATION_MESSAGE
    assert "cbam:view" in body["permissionsDefined"]
    # No compliance / calculation claims in contract
    lowered = str(body).lower()
    assert "compliant" not in lowered
    assert "see calculated" not in lowered
    assert body["calculationImplemented"] is False


def test_cbam_module_status_viewer_allowed(client: TestClient) -> None:
    token = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, token)
    response = client.get(_status_url(org_id), headers=auth_headers(token))
    assert response.status_code == 200


def test_cbam_module_status_system_admin(client: TestClient) -> None:
    token = api_login(client, "admin@ecotrace.dev", "EcoTraceAdmin!2024")
    # System admin may not have membership listing; use demo org by slug via org list
    orgs = client.get("/api/v1/organizations", headers=auth_headers(token))
    assert orgs.status_code == 200
    org_id = orgs.json()["items"][0]["id"]
    response = client.get(_status_url(org_id), headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["foundationAvailable"] is True


def test_cbam_module_status_cross_tenant_returns_404(client: TestClient, engine) -> None:
    token = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    headers = auth_headers(token)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db: Session = session_factory()
    try:
        db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()
        other = Organization(
            id=uuid.uuid4(),
            name="CBAM Isolation Org",
            slug="cbam-isolation-org",
            country_code="US",
            timezone="UTC",
            is_active=True,
        )
        db.add(other)
        db.commit()
        other_id = other.id
    finally:
        db.close()
    response = client.get(_status_url(other_id), headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_cbam_module_status_unknown_org_returns_404(client: TestClient) -> None:
    token = api_login(client, "analyst@ecotrace.dev", "EcoTraceAnalyst!2024")
    response = client.get(_status_url(uuid.uuid4()), headers=auth_headers(token))
    assert response.status_code == 404
