"""Phase 8C indirect-emissions allocation HTTP API contract tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from tests.cbam_api_profile_helpers import create_published_steel_profile
from tests.helpers import api_login, auth_headers, current_org_id

WORKBOOK_MONTHS = [
    ("2024-07-15", "176034.53", "506", "39.34"),
    ("2024-08-15", "180962.85", "421", "29.69"),
    ("2024-09-15", "144768.90", "337", "34.56"),
]


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f"/api/v1/cbam/organizations/{org_id}"


def _iea(org_id: str, binding_id: str) -> str:
    return f"{_base(org_id)}/reporting-period-bindings/{binding_id}/indirect-emissions-allocation"


def _prepare_binding(
    client: TestClient,
    token: str,
    org_id: str,
    *,
    start: str = "2024-07-01",
    end: str = "2024-09-30",
) -> tuple[str, str]:
    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(token)
    ).json()["items"]
    inst = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(token),
        json={
            "facilityId": facilities[0]["id"],
            "code": f"IEA-{uuid.uuid4().hex[:8]}",
            "name": "IEA API Installation",
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(token),
        json={
            "code": f"IEAP-{uuid.uuid4().hex[:6]}",
            "name": "IEA API Period",
            "periodType": "custom",
            "startDate": start,
            "endDate": end,
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


def _manual_factor() -> dict:
    return {
        "value": "0.439",
        "unit": "tCO2e/MWh",
        "sourceName": "Workbook H4",
        "sourceDocument": "SKDM_Alokasyon_Sablon.xlsx",
        "datasetVersion": "workbook-example",
        "referenceDescription": "Example EF",
        "effectiveDate": "2024-01-01",
    }


def _seed_ready(client: TestClient, token: str, org_id: str) -> tuple[str, str]:
    binding_id, installation_id = _prepare_binding(client, token, org_id)
    for day, qty, d, e in WORKBOOK_MONTHS:
        act = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
            headers=_auth(token),
            json={
                "installationProfileId": installation_id,
                "activityType": "ELECTRICITY",
                "quantity": qty,
                "unit": "kWh",
                "dataSourceType": "PRIMARY",
                "activityDate": day,
            },
        )
        assert act.status_code == 201, act.text
        pe = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/purchased-electricity/executions",
            headers=_auth(token),
            json={
                "clientRequestId": str(uuid.uuid4()),
                "activityRecordId": act.json()["id"],
                "factorSourceMode": "MANUAL",
                "manualFactor": _manual_factor(),
            },
        )
        assert pe.status_code in (200, 201), pe.text
        mb = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/monthly-production-basis",
            headers=_auth(token),
            json={
                "monthStart": f"{day[:8]}01",
                "totalProductionQuantity": d,
                "cbamQuantity": e,
                "quantityUnit": "t",
            },
        )
        assert mb.status_code == 201, mb.text
        profile_id = create_published_steel_profile(client, token, org_id, headers=_auth(token))
        prod = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
            headers=_auth(token),
            json={
                "installationProfileId": installation_id,
                "productProfileVersionId": profile_id,
                "quantity": e,
                "unit": "t",
                "productionDate": day,
            },
        )
        assert prod.status_code == 201, prod.text
    return binding_id, installation_id


def test_iea_api_readiness_execute_summary_and_permissions(client: TestClient) -> None:
    token = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, token)
    binding_id, _ = _seed_ready(client, token, org_id)
    base = _iea(org_id, binding_id)

    ready = client.get(f"{base}/readiness", headers=_auth(token))
    assert ready.status_code == 200, ready.text
    assert ready.json()["allocationReady"] is True

    client_id = str(uuid.uuid4())
    first = client.post(
        f"{base}/executions",
        headers=_auth(token),
        json={"clientRequestId": client_id},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["balanceStatus"] == "BALANCED"
    assert body["cbamElectricityMwh"] == "41.29445720"
    assert body["cbamIndirectEmissionsTco2e"] == "18.12826671"
    assert body["idempotentReplay"] is False

    replay = client.post(
        f"{base}/executions",
        headers=_auth(token),
        json={"clientRequestId": client_id},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotentReplay"] is True
    assert replay.json()["resultId"] == body["resultId"]

    detail = client.get(f"{base}/results/{body['resultId']}", headers=_auth(token))
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["sources"]) == 3
    assert len(detail.json()["products"]) == 3

    summary = client.get(f"{base}/summary", headers=_auth(token))
    assert summary.status_code == 200, summary.text
    assert summary.json()["currentResultId"] == body["resultId"]

    listed = client.get(f"{base}/results", headers=_auth(token))
    assert listed.status_code == 200, listed.text
    assert listed.json()["totalItems"] >= 1

    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    assert client.get(f"{base}/readiness", headers=_auth(viewer)).status_code == 200
    deny = client.post(
        f"{base}/executions",
        headers=_auth(viewer),
        json={"clientRequestId": str(uuid.uuid4())},
    )
    assert deny.status_code in (403, 401)
