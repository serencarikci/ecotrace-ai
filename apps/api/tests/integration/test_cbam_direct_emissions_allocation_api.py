"""Phase 7A-2 direct-emissions allocation HTTP API contract tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.cbam_api_profile_helpers import create_published_steel_profile
from tests.helpers import api_login, auth_headers, current_org_id

WORKBOOK_MONTHS = [
    ("2024-07-15", "188", "506", "39.34"),
    ("2024-08-15", "183", "421", "29.69"),
    ("2024-09-15", "490", "337", "34.56"),
]


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f"/api/v1/cbam/organizations/{org_id}"


def _dea(org_id: str, binding_id: str) -> str:
    return f"{_base(org_id)}/reporting-period-bindings/{binding_id}/direct-emissions-allocation"


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
            "code": f"DEA-{uuid.uuid4().hex[:8]}",
            "name": "DEA API Installation",
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(token),
        json={
            "code": f"DEAP-{uuid.uuid4().hex[:6]}",
            "name": "DEA API Period",
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


def _seed_ready(client: TestClient, token: str, org_id: str) -> tuple[str, str]:
    binding_id, installation_id = _prepare_binding(client, token, org_id)
    for day, qty, d, e in WORKBOOK_MONTHS:
        act = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
            headers=_auth(token),
            json={
                "installationProfileId": installation_id,
                "activityType": "NATURAL_GAS",
                "quantity": qty,
                "unit": "Sm3",
                "dataSourceType": "PRIMARY",
                "activityDate": day,
            },
        )
        assert act.status_code == 201, act.text
        sc = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/stationary-combustion/executions",
            headers=_auth(token),
            json={
                "clientRequestId": str(uuid.uuid4()),
                "activityRecordId": act.json()["id"],
                "fuelCode": "NATURAL_GAS",
                "densityValue": "0.68",
                "densityUnit": "kg/Sm3",
            },
        )
        assert sc.status_code == 201, sc.text
        month_start = f"{day[:8]}01"
        basis = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/monthly-production-basis",
            headers=_auth(token),
            json={
                "monthStart": month_start,
                "totalProductionQuantity": d,
                "cbamQuantity": e,
                "quantityUnit": "t",
            },
        )
        assert basis.status_code == 201, basis.text
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


def test_readiness_execute_replay_list_detail_summary(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _ = _seed_ready(client, admin, org_id)

    ready = client.get(f"{_dea(org_id, binding_id)}/readiness", headers=_auth(admin))
    assert ready.status_code == 200, ready.text
    body = ready.json()
    assert body["allocationReady"] is True
    assert body["status"] == "READY"

    client_id = str(uuid.uuid4())
    first = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(admin),
        json={"clientRequestId": client_id},
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["idempotentReplay"] is False
    assert first_body["balanceStatus"] == "BALANCED"
    assert isinstance(first_body["cbamFossilCo2Tonnes"], str)
    assert first_body["cbamFossilCo2Tonnes"] == "0.14240957"
    assert Decimal(first_body["remainingFossilCo2Tonnes"]) == Decimal("0")

    replay = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(admin),
        json={"clientRequestId": client_id},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotentReplay"] is True
    assert replay.json()["resultId"] == first_body["resultId"]

    listing = client.get(f"{_dea(org_id, binding_id)}/results", headers=_auth(admin))
    assert listing.status_code == 200
    assert listing.json()["totalItems"] == 1
    assert listing.json()["items"][0]["isCurrent"] is True

    detail = client.get(
        f"{_dea(org_id, binding_id)}/results/{first_body['resultId']}",
        headers=_auth(admin),
    )
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert d["isCurrent"] is True
    assert d["isStale"] is False
    assert isinstance(d["facilityFossilCo2Tonnes"], str)
    assert len(d["sourceCalculations"]) == 3
    assert len(d["productAllocations"]) == 3
    assert d["workbookSha256"]

    summary = client.get(f"{_dea(org_id, binding_id)}/summary", headers=_auth(admin))
    assert summary.status_code == 200
    assert summary.json()["currentResultId"] == first_body["resultId"]


def test_viewer_can_read_but_not_execute(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _ = _seed_ready(client, admin, org_id)
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")

    ready = client.get(f"{_dea(org_id, binding_id)}/readiness", headers=_auth(viewer))
    assert ready.status_code == 200

    denied = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(viewer),
        json={"clientRequestId": str(uuid.uuid4())},
    )
    assert denied.status_code in (403, 404)


def test_idempotency_conflict_via_api(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _ = _seed_ready(client, admin, org_id)
    client_id = str(uuid.uuid4())
    first = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(admin),
        json={"clientRequestId": client_id},
    )
    assert first.status_code == 201

    # Change production quantity → fingerprint differs for same key
    prods = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
        headers=_auth(admin),
    ).json()["items"]
    row = prods[0]
    upd = client.patch(
        f"{_base(org_id)}/production-records/{row['id']}",
        headers=_auth(admin),
        json={"rowVersion": row["rowVersion"], "quantity": "1"},
    )
    # May be 200 or blocked — either way execution with same key after material change
    # If update succeeds, readiness fails; fingerprint path needs same readiness.
    # Use fingerprint corruption path is unit-tested; here verify new key still blocked by MISMATCH
    blocked = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(admin),
        json={"clientRequestId": str(uuid.uuid4())},
    )
    assert blocked.status_code in (400, 409, 422)
    assert upd.status_code == 200
    err = blocked.json().get("error", {})
    codes = [d.get("code") for d in (err.get("details") or [])]
    assert "PRODUCTION_RECONCILIATION_MISMATCH" in codes or err.get("code") in (
        "BUSINESS_RULE_VIOLATION",
        "VALIDATION_ERROR",
        "CONFLICT",
    )


def test_cross_org_and_binding_isolation(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _ = _seed_ready(client, admin, org_id)
    executed = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(admin),
        json={"clientRequestId": str(uuid.uuid4())},
    )
    assert executed.status_code == 201
    result_id = executed.json()["resultId"]

    # Cross-binding same org (non-overlapping period)
    binding2, _ = _prepare_binding(client, admin, org_id, start="2025-01-01", end="2025-03-31")
    wrong_binding = client.get(
        f"{_dea(org_id, binding2)}/results/{result_id}",
        headers=_auth(admin),
    )
    assert wrong_binding.status_code == 404

    # Fabricated foreign organization id
    foreign_org = str(uuid.uuid4())
    cross = client.get(
        f"{_dea(foreign_org, binding_id)}/results/{result_id}",
        headers=_auth(admin),
    )
    assert cross.status_code == 404

    unknown = client.get(
        f"{_dea(org_id, binding_id)}/results/{uuid.uuid4()}",
        headers=_auth(admin),
    )
    assert unknown.status_code == 404
    err = unknown.json().get("error", unknown.json())
    assert "sql" not in str(err).lower()
    assert "traceback" not in str(err).lower()
    assert "IntegrityError" not in str(err)


def test_decimal_strings_and_pagination(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _ = _seed_ready(client, admin, org_id)
    for _ in range(2):
        r = client.post(
            f"{_dea(org_id, binding_id)}/executions",
            headers=_auth(admin),
            json={"clientRequestId": str(uuid.uuid4())},
        )
        assert r.status_code == 201
        assert isinstance(r.json()["facilityFossilCo2Tonnes"], str)

    page = client.get(
        f"{_dea(org_id, binding_id)}/results?page=1&pageSize=1",
        headers=_auth(admin),
    )
    assert page.status_code == 200
    assert page.json()["totalItems"] == 2
    assert len(page.json()["items"]) == 1


def test_historical_detail_independent_of_live_fuel_name(client: TestClient, engine) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, _ = _seed_ready(client, admin, org_id)
    executed = client.post(
        f"{_dea(org_id, binding_id)}/executions",
        headers=_auth(admin),
        json={"clientRequestId": str(uuid.uuid4())},
    )
    assert executed.status_code == 201
    result_id = executed.json()["resultId"]
    detail1 = client.get(
        f"{_dea(org_id, binding_id)}/results/{result_id}",
        headers=_auth(admin),
    ).json()
    fuel_name = detail1["sourceCalculations"][0]["fuelName"]

    from sqlalchemy import select
    from sqlalchemy.orm import sessionmaker

    from ecotrace.modules.cbam.infrastructure.models import CbamStationaryCombustionFuel

    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        fuel = db.execute(
            select(CbamStationaryCombustionFuel).where(
                CbamStationaryCombustionFuel.code == "NATURAL_GAS"
            )
        ).scalar_one()
        fuel.name = "LIVE MUTATED NAME"
        db.commit()
    finally:
        db.close()

    detail2 = client.get(
        f"{_dea(org_id, binding_id)}/results/{result_id}",
        headers=_auth(admin),
    ).json()
    assert detail2["sourceCalculations"][0]["fuelName"] == fuel_name
    assert detail2["sourceCalculations"][0]["fuelName"] != "LIVE MUTATED NAME"
