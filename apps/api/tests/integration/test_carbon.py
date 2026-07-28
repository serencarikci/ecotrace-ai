from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.db.seed import run_seed
from ecotrace.modules.emission_factors.infrastructure.models import EmissionFactor
from helpers import api_login as _login
from helpers import auth_headers as _auth
from helpers import current_org_id as _org_id


def test_factor_source_crud_authorization(client: TestClient) -> None:
    admin = _login(client, "admin@ecotrace.dev", "EcoTraceAdmin!2024")
    create = client.post(
        "/api/v1/emission-factor-sources",
        headers=_auth(admin),
        json={
            "code": "TEST_SRC",
            "name": "Test Source",
            "publisher": "EcoTrace",
            "isDemo": True,
        },
    )
    assert create.status_code == 201, create.text
    source_id = create.json()["id"]

    analyst = _login(client, "analyst@ecotrace.dev", "EcoTraceAnalyst!2024")
    denied = client.post(
        "/api/v1/emission-factor-sources",
        headers=_auth(analyst),
        json={"code": "NOPE", "name": "Nope"},
    )
    assert denied.status_code == 403

    listed = client.get("/api/v1/emission-factor-sources", headers=_auth(admin))
    assert listed.status_code == 200
    assert any(i["code"] == "TEST_SRC" for i in listed.json()["items"])

    archived = client.post(
        f"/api/v1/emission-factor-sources/{source_id}/archive", headers=_auth(admin)
    )
    assert archived.status_code == 200
    assert archived.json()["isActive"] is False


def test_inventory_calculate_and_isolation(client: TestClient) -> None:
    token = _login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = _org_id(client, token)

    periods = client.get(f"/api/v1/organizations/{org_id}/reporting-periods", headers=_auth(token))
    assert periods.status_code == 200
    period = next(p for p in periods.json()["items"] if p["code"] == "2024-Q1")

    inv = client.post(
        f"/api/v1/organizations/{org_id}/carbon-inventories",
        headers=_auth(token),
        json={
            "reportingPeriodId": period["id"],
            "name": "Integration Inventory",
            "description": "test",
            "gwpDatasetCode": "AR5-demo",
        },
    )
    assert inv.status_code == 201, inv.text
    inventory_id = inv.json()["id"]

    validation = client.post(
        f"/api/v1/organizations/{org_id}/carbon-inventories/{inventory_id}/validate",
        headers=_auth(token),
    )
    assert validation.status_code == 200, validation.text
    body = validation.json()
    assert "valid" in body
    assert "missingFactors" in body

    calc = client.post(
        f"/api/v1/organizations/{org_id}/carbon-inventories/{inventory_id}/calculate",
        headers=_auth(token),
        json={"partialCalculation": True},
    )
    assert calc.status_code == 200, calc.text
    assert calc.json()["engineVersion"] == "3.0.0"
    assert Decimal(str(calc.json()["totalKgCo2e"] or "0")) >= 0

    summary = client.get(
        f"/api/v1/organizations/{org_id}/carbon-inventories/{inventory_id}/summary",
        headers=_auth(token),
    )
    assert summary.status_code == 200
    assert "totalTCo2e" in summary.json()

    fake_org = "00000000-0000-0000-0000-000000000099"
    blocked = client.get(
        f"/api/v1/organizations/{fake_org}/carbon-inventories/{inventory_id}",
        headers=_auth(token),
    )
    assert blocked.status_code == 404


def test_factor_activation_and_clone(client: TestClient) -> None:
    admin = _login(client, "admin@ecotrace.dev", "EcoTraceAdmin!2024")

    sources = client.get("/api/v1/emission-factor-sources", headers=_auth(admin)).json()["items"]
    source_id = sources[0]["id"]
    types = client.get("/api/v1/reference/activity-types", headers=_auth(admin)).json()["items"]
    electricity = next(t for t in types if t["code"] == "purchased_electricity")

    draft = client.post(
        "/api/v1/emission-factors",
        headers=_auth(admin),
        json={
            "sourceId": source_id,
            "code": "EF-TEST-CLONE",
            "name": "Clone test factor",
            "activityTypeId": electricity["id"],
            "scope": "scope_2",
            "category": "purchased_electricity",
            "geographyCode": "ZZ",
            "unitCode": "kWh",
            "factorValue": "0.1",
            "version": 1,
            "validFrom": "2024-01-01",
            "validTo": "2024-12-31",
        },
    )
    assert draft.status_code == 201, draft.text
    factor_id = draft.json()["id"]

    activated = client.post(f"/api/v1/emission-factors/{factor_id}/activate", headers=_auth(admin))
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "active"

    cloned = client.post(
        f"/api/v1/emission-factors/{factor_id}/clone-version", headers=_auth(admin)
    )
    assert cloned.status_code == 201
    assert cloned.json()["version"] == 2
    assert cloned.json()["status"] == "draft"

    edit = client.patch(
        f"/api/v1/emission-factors/{factor_id}",
        headers=_auth(admin),
        json={"factorValue": "0.2"},
    )
    assert edit.status_code == 400


def test_matching_preview(client: TestClient) -> None:
    token = _login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = _org_id(client, token)
    types = client.get("/api/v1/reference/activity-types", headers=_auth(token)).json()["items"]
    electricity = next(t for t in types if t["code"] == "purchased_electricity")
    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(token)
    ).json()["items"]
    facility = next(f for f in facilities if f["code"] == "IZM-PROD")

    preview = client.post(
        f"/api/v1/organizations/{org_id}/factor-matching/preview",
        headers=_auth(token),
        json={
            "activityTypeId": electricity["id"],
            "facilityId": facility["id"],
            "activityDate": "2024-02-15",
            "quantity": "1000",
            "unitCode": "kWh",
        },
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["ambiguityStatus"] is False
    assert body["selectedFactor"] is not None
    assert body["selectedFactor"]["geographyCode"] == "TR"


def test_seed_idempotency_carbon(seeded_db: Session) -> None:
    count1 = len(seeded_db.execute(select(EmissionFactor)).scalars().all())
    run_seed(seeded_db)
    seeded_db.commit()
    count2 = len(seeded_db.execute(select(EmissionFactor)).scalars().all())
    assert count1 == count2
    assert count2 >= 10
