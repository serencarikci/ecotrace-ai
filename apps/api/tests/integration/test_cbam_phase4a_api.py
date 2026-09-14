from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from tests.cbam_api_profile_helpers import create_published_steel_profile
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
            "code": f"A4-{uuid.uuid4().hex[:8]}",
            "name": "Alloc Installation",
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(token),
        json={
            "code": f"A4P-{uuid.uuid4().hex[:6]}",
            "name": "Alloc Period",
            "periodType": "custom",
            "startDate": "2030-01-01",
            "endDate": "2030-03-31",
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


def test_allocation_api_authz_lifecycle_and_execution(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    profile_id = create_published_steel_profile(client, admin, org_id, headers=_auth(admin))

    denied = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(viewer),
        json={
            "installationProfileId": installation_id,
            "allocationMethod": "DIRECT_ASSIGNMENT",
            "name": "Viewer denied",
        },
    )
    assert denied.status_code == 403

    base_prod = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "productProfileVersionId": profile_id,
            "quantity": "500",
            "unit": "t",
        },
    )
    assert base_prod.status_code == 201, base_prod.text
    target_prod = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "productProfileVersionId": profile_id,
            "quantity": "100",
            "unit": "t",
        },
    )
    assert target_prod.status_code == 201, target_prod.text
    activity = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "activityType": "ELECTRICITY",
            "quantity": "100",
            "unit": "MWh",
            "dataSourceType": "PRIMARY",
        },
    )
    assert activity.status_code == 201, activity.text

    created = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "allocationMethod": "PRODUCTION_QUANTITY_RATIO",
            "name": "API ratio",
            "numeratorProductionRecordId": target_prod.json()["id"],
            "denominatorProductionRecordId": base_prod.json()["id"],
        },
    )
    assert created.status_code == 201, created.text
    rule = created.json()
    assert rule["allocationRatio"] == "0.200000000000"
    assert rule["status"] == "DRAFT"
    rule_id = rule["id"]

    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(viewer),
    )
    assert listed.status_code == 200
    assert any(item["id"] == rule_id for item in listed.json()["items"])

    stale = client.patch(
        f"{_base(org_id)}/allocation-rules/{rule_id}",
        headers=_auth(admin),
        json={"rowVersion": 999, "name": "Stale"},
    )
    assert stale.status_code == 409

    activated = client.post(
        f"{_base(org_id)}/allocation-rules/{rule_id}/activate",
        headers=_auth(admin),
        json={"rowVersion": rule["rowVersion"]},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["status"] == "ACTIVE"

    invalid_second = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "allocationMethod": "DIRECT_ASSIGNMENT",
            "name": "Second active attempt",
        },
    )
    assert invalid_second.status_code == 201
    second_id = invalid_second.json()["id"]
    conflict = client.post(
        f"{_base(org_id)}/allocation-rules/{second_id}/activate",
        headers=_auth(admin),
        json={"rowVersion": invalid_second.json()["rowVersion"]},
    )
    assert conflict.status_code == 409

    allocated = client.post(
        f"{_base(org_id)}/allocation-rules/{rule_id}/allocate/activity-records/"
        f"{activity.json()['id']}",
        headers=_auth(admin),
    )
    assert allocated.status_code == 201, allocated.text
    body = allocated.json()
    assert body["allocationRatio"] == "0.200000000000"
    assert body["allocatedQuantity"] == "20.00000000"
    assert body["sourceQuantity"] == "100.00000000"
    assert body["allocatedUnit"] == "MWh"
    assert "emissionFactor" not in body
    assert "co2e" not in body
    assert "co2e" not in str(body).lower()

    results = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-results",
        headers=_auth(viewer),
    )
    assert results.status_code == 200
    assert results.json()["totalItems"] >= 1

    recalculated = client.post(
        f"{_base(org_id)}/allocation-results/{body['id']}/recalculate",
        headers=_auth(admin),
    )
    assert recalculated.status_code == 201, recalculated.text
    assert recalculated.json()["isCurrent"] is True
    assert recalculated.json()["id"] != body["id"]

    archived = client.post(
        f"{_base(org_id)}/allocation-rules/{rule_id}/archive",
        headers=_auth(admin),
        json={"rowVersion": activated.json()["rowVersion"]},
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"

    blocked = client.post(
        f"{_base(org_id)}/allocation-rules/{rule_id}/allocate/activity-records/"
        f"{activity.json()['id']}",
        headers=_auth(admin),
    )
    assert blocked.status_code == 400


def test_allocation_org_isolation(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    create_published_steel_profile(client, admin, org_id, headers=_auth(admin))
    created = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "allocationMethod": "DIRECT_ASSIGNMENT",
            "name": "Isolation",
        },
    )
    assert created.status_code == 201
    other_org = str(uuid.uuid4())
    missing = client.get(
        f"{_base(other_org)}/allocation-rules/{created.json()['id']}",
        headers=_auth(admin),
    )
    assert missing.status_code in (403, 404)
