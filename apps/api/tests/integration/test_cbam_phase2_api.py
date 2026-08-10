from __future__ import annotations

import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from tests.helpers import api_login, auth_headers, current_org_id

from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.products.infrastructure.models import Product
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f"/api/v1/cbam/organizations/{org_id}"


def test_cbam_phase2_paths_registered(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert f"{_base('{organization_id}')}/installations" in paths or any(
        "/installations" in p for p in paths
    )
    assert any("reporting-period-bindings" in p for p in paths)
    assert any("product-profile-versions" in p for p in paths)


def test_installation_crud_activate_archive_and_authz(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, admin)
    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(admin)
    ).json()["items"]
    facility_id = facilities[0]["id"]
    code = f"API-INST-{uuid.uuid4().hex[:8]}"

    denied = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(viewer),
        json={"facilityId": facility_id, "code": code, "name": "Viewer Denied"},
    )
    assert denied.status_code == 403

    created = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(admin),
        json={"facilityId": facility_id, "code": code, "name": "API Installation"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "draft"
    assert body["rowVersion"] == 1
    installation_id = body["id"]

    listed = client.get(f"{_base(org_id)}/installations", headers=_auth(viewer))
    assert listed.status_code == 200
    assert any(item["id"] == installation_id for item in listed.json()["items"])

    patched = client.patch(
        f"{_base(org_id)}/installations/{installation_id}",
        headers=_auth(admin),
        json={"rowVersion": 1, "name": "Renamed Installation"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Renamed Installation"
    assert patched.json()["rowVersion"] == 2

    stale = client.patch(
        f"{_base(org_id)}/installations/{installation_id}",
        headers=_auth(admin),
        json={"rowVersion": 1, "name": "Stale"},
    )
    assert stale.status_code == 409

    activated = client.post(
        f"{_base(org_id)}/installations/{installation_id}/activate",
        headers=_auth(admin),
        json={"rowVersion": 2},
    )
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"

    archived = client.post(
        f"{_base(org_id)}/installations/{installation_id}/archive",
        headers=_auth(admin),
        json={"rowVersion": activated.json()["rowVersion"]},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_period_binding_open_data_collection_flow(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(admin)
    ).json()["items"]
    inst = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(admin),
        json={
            "facilityId": facilities[0]["id"],
            "code": f"PER-INST-{uuid.uuid4().hex[:8]}",
            "name": "Period Inst",
        },
    )
    assert inst.status_code == 201

    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(admin),
        json={
            "code": f"CBAM-P-{uuid.uuid4().hex[:6]}",
            "name": "CBAM Period",
            "periodType": "custom",
            "startDate": "2027-01-01",
            "endDate": "2027-03-31",
        },
    )
    assert period.status_code == 201, period.text
    period_id = period.json()["id"]

    binding = client.post(
        f"{_base(org_id)}/reporting-period-bindings",
        headers=_auth(admin),
        json={"reportingPeriodId": period_id},
    )
    assert binding.status_code == 201, binding.text
    assert binding.json()["status"] == "draft"
    binding_id = binding.json()["id"]

    opened = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/open-data-collection",
        headers=_auth(admin),
        json={"rowVersion": 1},
    )
    assert opened.status_code == 200, opened.text
    assert opened.json()["status"] == "data_collection"

    blocked = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/open-data-collection",
        headers=_auth(admin),
        json={"rowVersion": opened.json()["rowVersion"]},
    )
    assert blocked.status_code == 400


def test_product_profile_api_no_classification(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    products = client.get(
        f"/api/v1/organizations/{org_id}/products", headers=_auth(admin)
    ).json()["items"]
    assert products
    product_id = products[0]["id"]
    version = 9000 + (uuid.uuid4().int % 1000)
    created = client.post(
        f"{_base(org_id)}/product-profile-versions",
        headers=_auth(admin),
        json={"productId": product_id, "version": version},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["classificationReady"] is False
    assert "cnCode" not in body
    assert body["status"] == "draft"

    detail = client.get(
        f"{_base(org_id)}/product-profile-versions/{body['id']}",
        headers=_auth(admin),
    )
    assert detail.status_code == 200
    assert detail.json()["classificationReady"] is False

    archived = client.post(
        f"{_base(org_id)}/product-profile-versions/{body['id']}/archive",
        headers=_auth(admin),
        json={"rowVersion": body["rowVersion"]},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_cross_tenant_installation_returns_404(client: TestClient, engine) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db: Session = session_factory()
    try:
        other = Organization(
            id=uuid.uuid4(),
            name="CBAM Cross Tenant",
            slug=f"cbam-x-{uuid.uuid4().hex[:8]}",
            country_code="US",
            timezone="UTC",
            is_active=True,
        )
        db.add(other)
        db.flush()
        facility = Facility(
            organization_id=other.id,
            code="X-FAC",
            name="Hidden",
            facility_type="office",
            country_code="US",
            timezone="UTC",
            is_active=True,
        )
        db.add(facility)
        db.commit()
        other_id = str(other.id)
        facility_id = str(facility.id)
    finally:
        db.close()

    response = client.get(
        f"{_base(other_id)}/installations",
        headers=_auth(admin),
    )
    assert response.status_code == 404

    create = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(admin),
        json={
            "facilityId": facility_id,
            "code": f"X-{uuid.uuid4().hex[:6]}",
            "name": "Should 404",
        },
    )
    assert create.status_code == 404


def test_wrong_org_period_and_product_refs_404(client: TestClient, engine) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db: Session = session_factory()
    try:
        other = Organization(
            id=uuid.uuid4(),
            name="CBAM Ref Org",
            slug=f"cbam-ref-{uuid.uuid4().hex[:8]}",
            country_code="DE",
            timezone="UTC",
            is_active=True,
        )
        db.add(other)
        db.flush()
        period = ReportingPeriod(
            organization_id=other.id,
            code="FOREIGN-P",
            name="Foreign Period",
            period_type="quarter",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            status="open",
        )
        product = Product(
            organization_id=other.id,
            code="FOREIGN-PROD",
            name="Foreign Product",
            product_type="finished_good",
            default_unit_code="unit",
            is_active=True,
        )
        db.add(period)
        db.add(product)
        db.commit()
        period_id = str(period.id)
        product_id = str(product.id)
    finally:
        db.close()

    binding = client.post(
        f"{_base(org_id)}/reporting-period-bindings",
        headers=_auth(admin),
        json={"reportingPeriodId": period_id},
    )
    assert binding.status_code == 404

    profile = client.post(
        f"{_base(org_id)}/product-profile-versions",
        headers=_auth(admin),
        json={"productId": product_id, "version": 1},
    )
    assert profile.status_code == 404
