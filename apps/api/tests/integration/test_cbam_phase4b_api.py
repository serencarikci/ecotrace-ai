from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from tests.helpers import api_login, auth_headers, current_org_id


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f"/api/v1/cbam/organizations/{org_id}"


def _prepare_binding(client: TestClient, token: str, org_id: str) -> tuple[str, str]:
    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(token)
    ).json()["items"]
    inst = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(token),
        json={
            "facilityId": facilities[0]["id"],
            "code": f"B4-{uuid.uuid4().hex[:8]}",
            "name": "Factor Installation",
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(token),
        json={
            "code": f"B4P-{uuid.uuid4().hex[:6]}",
            "name": "Factor Period",
            "periodType": "custom",
            "startDate": "2031-01-01",
            "endDate": "2031-03-31",
        },
    )
    assert period.status_code == 201, period.text
    binding = client.post(
        f"{_base(org_id)}/reporting-period-bindings",
        headers=_auth(token),
        json={"reportingPeriodId": period.json()["id"]},
    )
    assert binding.status_code == 201, binding.text
    opened = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding.json()['id']}/open-data-collection",
        headers=_auth(token),
        json={"rowVersion": binding.json()["rowVersion"]},
    )
    assert opened.status_code == 200, opened.text
    return opened.json()["id"], inst.json()["id"]


def test_factor_resolution_api_flow(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)

    sources = client.get(f"{_base(org_id)}/reference-sources", headers=_auth(viewer))
    assert sources.status_code == 200
    assert any(s["code"] == "IPCC" for s in sources.json()["items"])

    defs = client.get(f"{_base(org_id)}/factor-definitions", headers=_auth(viewer))
    assert defs.status_code == 200
    ncv = next(d for d in defs.json()["items"] if d["code"] == "NET_CALORIFIC_VALUE")
    manual = next(s for s in sources.json()["items"] if s["code"] == "MANUAL_APPROVED_REFERENCE")

    denied = client.post(
        f"{_base(org_id)}/factor-definitions/{ncv['id']}/values",
        headers=_auth(viewer),
        json={
            "referenceSourceId": manual["id"],
            "activityType": "DIESEL",
            "numericValue": "36.0",
            "unit": "MJ/L",
            "dataSourceType": "DEFAULT_REFERENCE",
        },
    )
    assert denied.status_code == 403

    created_value = client.post(
        f"{_base(org_id)}/factor-definitions/{ncv['id']}/values",
        headers=_auth(admin),
        json={
            "referenceSourceId": manual["id"],
            "activityType": "DIESEL",
            "numericValue": "36.0",
            "unit": "MJ/L",
            "dataSourceType": "DEFAULT_REFERENCE",
            "validFrom": "2030-01-01",
            "validUntil": "2035-12-31",
        },
    )
    assert created_value.status_code == 201, created_value.text
    activated = client.post(
        f"{_base(org_id)}/factor-values/{created_value.json()['id']}/activate",
        headers=_auth(admin),
        json={"rowVersion": created_value.json()["rowVersion"]},
    )
    assert activated.status_code == 200

    activity = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "activityType": "DIESEL",
            "quantity": "500",
            "unit": "L",
            "dataSourceType": "PRIMARY",
            "activityDate": "2031-02-01",
            "properties": [
                {
                    "propertyCode": "NET_CALORIFIC_VALUE",
                    "numericValue": "35.8",
                    "unit": "MJ/L",
                    "sourceType": "PRIMARY",
                    "sourceReference": "cert",
                }
            ],
        },
    )
    assert activity.status_code == 201, activity.text

    resolve_denied = client.post(
        f"{_base(org_id)}/activity-records/{activity.json()['id']}"
        "/factor-resolutions/NET_CALORIFIC_VALUE/resolve",
        headers=_auth(viewer),
    )
    assert resolve_denied.status_code == 403

    resolved = client.post(
        f"{_base(org_id)}/activity-records/{activity.json()['id']}"
        "/factor-resolutions/NET_CALORIFIC_VALUE/resolve",
        headers=_auth(admin),
    )
    assert resolved.status_code == 201, resolved.text
    body = resolved.json()
    assert body["resolutionStatus"] == "RESOLVED_PRIMARY"
    assert body["selectedValue"] == "35.80000000"
    assert body["selectedUnit"] == "MJ/L"
    assert "co2e" not in body
    assert "calculatedEmission" not in body

    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/factor-resolutions",
        headers=_auth(viewer),
    )
    assert listed.status_code == 200
    assert listed.json()["totalItems"] >= 1
