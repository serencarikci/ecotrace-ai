from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.helpers import api_login, auth_headers, current_org_id

JANUARY_SM3 = "105437.03007518797"
EXPECTED_TCO2 = "190.22695917"


def _error_details(response) -> list:
    body = response.json()
    return body.get("error", {}).get("details", []) or body.get("details", [])


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f"/api/v1/cbam/organizations/{org_id}"


def _exec_body(**overrides) -> dict:
    body = {
        "clientRequestId": str(uuid.uuid4()),
        "fuelCode": "NATURAL_GAS",
        "densityValue": "0.67",
        "densityUnit": "kg/Sm3",
    }
    body.update(overrides)
    return body


def _prepare_binding(
    client: TestClient,
    token: str,
    org_id: str,
    *,
    start: str = "2024-01-01",
    end: str = "2024-03-31",
) -> tuple[str, str]:
    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(token)
    ).json()["items"]
    inst = client.post(
        f"{_base(org_id)}/installations",
        headers=_auth(token),
        json={
            "facilityId": facilities[0]["id"],
            "code": f"SC4A-{uuid.uuid4().hex[:8]}",
            "name": "SC API Installation",
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(token),
        json={
            "code": f"SC4AP-{uuid.uuid4().hex[:6]}",
            "name": "SC API Period",
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


def _create_ng_activity(
    client: TestClient,
    token: str,
    org_id: str,
    binding_id: str,
    installation_id: str,
    *,
    activity_date: str | None = "2024-01-15",
    quantity: str = JANUARY_SM3,
    unit: str = "Sm3",
) -> dict:
    body: dict = {
        "installationProfileId": installation_id,
        "activityType": "NATURAL_GAS",
        "quantity": quantity,
        "unit": unit,
        "dataSourceType": "PRIMARY",
    }
    if activity_date is not None:
        body["activityDate"] = activity_date
    response = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(token),
        json=body,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_viewer_can_list_active_fuels(client: TestClient) -> None:
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, viewer)
    response = client.get(
        f"{_base(org_id)}/stationary-combustion/fuels",
        headers=_auth(viewer),
    )
    assert response.status_code == 200, response.text
    codes = {item["code"] for item in response.json()}
    assert "NATURAL_GAS" in codes
    ng = next(item for item in response.json() if item["code"] == "NATURAL_GAS")
    assert ng["inputBasis"] == "VOLUME"
    assert ng["densityRequired"] is True
    assert ng["status"] == "ACTIVE"


def test_unauthenticated_or_no_view_denied_for_fuels(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    denied = client.get(f"{_base(org_id)}/stationary-combustion/fuels")
    assert denied.status_code == 401


def test_natural_gas_parameter_resolution(client: TestClient) -> None:
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, viewer)
    response = client.get(
        f"{_base(org_id)}/stationary-combustion/fuels/NATURAL_GAS/parameters",
        headers=_auth(viewer),
        params={"referenceDate": "2024-06-15"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["netCalorificValue"] == "48.00000000" or Decimal(
        body["netCalorificValue"]
    ) == Decimal("48")
    assert Decimal(body["fossilCo2EmissionFactor"]) == Decimal("56100")
    assert Decimal(body["oxidationFactor"]) == Decimal("1")
    assert body["referenceDensity"] is None
    assert body["densityRequired"] is True
    assert body["resolutionStatus"] == "RESOLVED"
    assert body["datasetVersion"] == "2006_V1"


def test_unresolved_date_and_unknown_fuel(client: TestClient) -> None:
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, viewer)
    unresolved = client.get(
        f"{_base(org_id)}/stationary-combustion/fuels/NATURAL_GAS/parameters",
        headers=_auth(viewer),
        params={"referenceDate": "1990-01-01"},
    )
    assert unresolved.status_code == 422
    assert any(d.get("code") == "UNRESOLVED_PARAMETER_SET" for d in _error_details(unresolved))
    unknown = client.get(
        f"{_base(org_id)}/stationary-combustion/fuels/UNKNOWN_FUEL/parameters",
        headers=_auth(viewer),
        params={"referenceDate": "2024-01-01"},
    )
    assert unknown.status_code == 404


def test_explicit_dataset_version(client: TestClient) -> None:
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, viewer)
    ok = client.get(
        f"{_base(org_id)}/stationary-combustion/fuels/NATURAL_GAS/parameters",
        headers=_auth(viewer),
        params={"referenceDate": "2024-01-01", "datasetVersion": "2006_V1"},
    )
    assert ok.status_code == 200
    missing = client.get(
        f"{_base(org_id)}/stationary-combustion/fuels/NATURAL_GAS/parameters",
        headers=_auth(viewer),
        params={"referenceDate": "2024-01-01", "datasetVersion": "NOPE"},
    )
    assert missing.status_code == 422


def test_january_golden_execution_and_result_detail(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    client_request_id = str(uuid.uuid4())

    denied = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(viewer),
        json=_exec_body(activityRecordId=activity["id"], clientRequestId=client_request_id),
    )
    assert denied.status_code in {403, 404}

    executed = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity["id"], clientRequestId=client_request_id),
    )
    assert executed.status_code == 201, executed.text
    body = executed.json()
    assert body["status"] == "COMPLETED"
    assert body["idempotentReplay"] is False
    assert body["clientRequestId"] == client_request_id
    assert Decimal(body["resultValue"]) == Decimal(EXPECTED_TCO2)
    assert body["resultUnit"] == "tCO2"
    assert body["referenceDate"] == "2024-01-15"
    assert "quantity" not in body

    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
        headers=_auth(viewer),
    )
    assert listed.status_code == 200
    assert listed.json()["totalItems"] == 1
    assert listed.json()["items"][0]["resultId"] == body["resultId"]
    assert listed.json()["items"][0]["clientRequestId"] == client_request_id

    detail = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results/{body['resultId']}",
        headers=_auth(viewer),
    )
    assert detail.status_code == 200, detail.text
    snap = detail.json()
    assert Decimal(snap["resultValue"]) == Decimal(EXPECTED_TCO2)
    assert Decimal(snap["densityValue"]) == Decimal("0.67")
    assert Decimal(snap["netCalorificValue"]) == Decimal("48")
    assert snap["datasetVersion"] == "2006_V1"
    assert snap["ncvSourceTable"] == "Table 1.2"
    assert snap["clientRequestId"] == client_request_id

    # No edit/delete routes
    assert (
        client.patch(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results/{body['resultId']}",
            headers=_auth(admin),
            json={},
        ).status_code
        == 405
    )
    assert (
        client.delete(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results/{body['resultId']}",
            headers=_auth(admin),
        ).status_code
        == 405
    )


def test_missing_density_and_failed_execution_no_result(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    failed = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json={
            "clientRequestId": str(uuid.uuid4()),
            "activityRecordId": activity["id"],
            "fuelCode": "NATURAL_GAS",
        },
    )
    assert failed.status_code == 422
    assert any(d.get("code") == "DENSITY_REQUIRED" for d in _error_details(failed))
    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
        headers=_auth(admin),
    )
    assert listed.json()["totalItems"] == 0


def test_invalid_density_and_incompatible_unit(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    invalid = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(
            activityRecordId=activity["id"],
            densityValue="0",
            densityUnit="kg/Sm3",
        ),
    )
    assert invalid.status_code == 422
    assert any(d.get("code") == "DENSITY_INVALID" for d in _error_details(invalid))


def test_reference_date_outside_period_when_no_activity_date(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(
        client, admin, org_id, binding_id, installation_id, activity_date=None
    )
    outside = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(
            activityRecordId=activity["id"],
            calculationReferenceDate="2025-01-01",
        ),
    )
    assert outside.status_code == 422
    assert any(d.get("code") == "REFERENCE_DATE_OUTSIDE_PERIOD" for d in _error_details(outside))


def test_cross_org_and_binding_isolation(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    executed = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity["id"]),
    )
    assert executed.status_code == 201, executed.text
    result_id = executed.json()["resultId"]

    other_binding, _ = _prepare_binding(client, admin, org_id, start="2025-01-01", end="2025-03-31")
    wrong_binding = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{other_binding}/stationary-combustion/results/{result_id}",
        headers=_auth(admin),
    )
    assert wrong_binding.status_code == 404

    foreign_org = uuid.uuid4()
    foreign = client.get(
        f"{_base(str(foreign_org))}/reporting-period-bindings/{binding_id}/stationary-combustion/results/{result_id}",
        headers=_auth(admin),
    )
    assert foreign.status_code in {403, 404}

    wrong_activity_binding = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{other_binding}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity["id"]),
    )
    assert wrong_activity_binding.status_code == 422
    assert any(
        d.get("code") == "ACTIVITY_BINDING_MISMATCH" for d in _error_details(wrong_activity_binding)
    )


def test_intentional_recalculation_new_client_request_id(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    first = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity["id"]),
    )
    assert first.status_code == 201
    second = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity["id"]),
    )
    assert second.status_code == 201
    assert second.json()["runId"] != first.json()["runId"]
    assert second.json()["resultId"] != first.json()["resultId"]
    assert second.json()["idempotentReplay"] is False

    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
        headers=_auth(admin),
        params={"pageSize": 10},
    )
    assert listed.json()["totalItems"] == 2


def test_result_list_pagination(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    for _ in range(3):
        activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
        response = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
            headers=_auth(admin),
            json=_exec_body(activityRecordId=activity["id"]),
        )
        assert response.status_code == 201
    page1 = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
        headers=_auth(admin),
        params={"page": 1, "pageSize": 2},
    )
    assert page1.status_code == 200
    assert page1.json()["totalItems"] == 3
    assert len(page1.json()["items"]) == 2
    page2 = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
        headers=_auth(admin),
        params={"page": 2, "pageSize": 2},
    )
    assert len(page2.json()["items"]) == 1


def test_period_summary_viewer_ready_and_flags(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)

    empty = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/summary",
        headers=_auth(viewer),
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["readinessStatus"] == "EMPTY"

    activity = _create_ng_activity(client, admin, org_id, binding_id, installation_id)
    incomplete = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/summary",
        headers=_auth(viewer),
    )
    assert incomplete.json()["readinessStatus"] == "INCOMPLETE"

    executed = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
        headers=_auth(admin),
        json=_exec_body(activityRecordId=activity["id"]),
    )
    assert executed.status_code == 201, executed.text
    summary = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/summary",
        headers=_auth(viewer),
    )
    assert summary.status_code == 200
    body = summary.json()
    assert body["readinessStatus"] == "READY"
    assert body["finalResultValue"] == EXPECTED_TCO2
    assert body["finalResultUnit"] == "tCO2"
    assert body["validCurrentResultCount"] == 1
    assert isinstance(body["finalResultValue"], str)

    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/results",
        headers=_auth(viewer),
    )
    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["isCurrent"] is True
    assert item["isStale"] is False
    assert item["resultId"] == executed.json()["resultId"]

    foreign = client.get(
        f"{_base(str(uuid.uuid4()))}/reporting-period-bindings/{binding_id}/stationary-combustion/summary",
        headers=_auth(viewer),
    )
    assert foreign.status_code in {403, 404}


def test_summary_requires_authenticated_user(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _installation_id = _prepare_binding(client, admin, org_id)
    unauth = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/summary",
    )
    assert unauth.status_code in {401, 403}
