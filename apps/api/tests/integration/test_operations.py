from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.activity_data.infrastructure.models import ActivityRecord
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reference_data.infrastructure.models import ActivityType
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod
from helpers import api_login as _login
from helpers import auth_headers as _auth
from helpers import current_org_id as _org_id


def test_facility_list_and_create(client: TestClient) -> None:
    token = _login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = _org_id(client, token)
    listed = client.get(f"/api/v1/organizations/{org_id}/facilities", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["totalItems"] >= 2

    created = client.post(
        f"/api/v1/organizations/{org_id}/facilities",
        headers=_auth(token),
        json={
            "code": "TEST-FAC",
            "name": "Test Facility",
            "facilityType": "office",
            "countryCode": "TR",
            "city": "Ankara",
            "timezone": "Europe/Istanbul",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["code"] == "TEST-FAC"


def test_cross_org_facility_denied(client: TestClient) -> None:
    admin = _login(client, "admin@ecotrace.dev", "EcoTraceAdmin!2024")
    other = client.post(
        "/api/v1/organizations",
        headers=_auth(admin),
        json={
            "name": "Other Org Ops",
            "slug": "other-org-ops",
            "countryCode": "DE",
            "timezone": "Europe/Berlin",
            "isActive": True,
        },
    )
    assert other.status_code == 201, other.text
    other_id = other.json()["id"]
    facility = client.post(
        f"/api/v1/organizations/{other_id}/facilities",
        headers=_auth(admin),
        json={
            "code": "OTHER",
            "name": "Other Facility",
            "facilityType": "office",
            "countryCode": "DE",
            "city": "Berlin",
            "timezone": "Europe/Berlin",
        },
    )
    assert facility.status_code == 201, facility.text
    facility_id = facility.json()["id"]

    token = _login(client, "analyst@ecotrace.dev", "EcoTraceAnalyst!2024")
    org_id = _org_id(client, token)
    response = client.get(
        f"/api/v1/organizations/{org_id}/facilities/{facility_id}",
        headers=_auth(token),
    )
    assert response.status_code == 404


def test_viewer_cannot_create_facility(client: TestClient) -> None:
    token = _login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = _org_id(client, token)
    response = client.post(
        f"/api/v1/organizations/{org_id}/facilities",
        headers=_auth(token),
        json={
            "code": "VIEW-FAIL",
            "name": "Should Fail",
            "facilityType": "office",
            "countryCode": "TR",
            "timezone": "Europe/Istanbul",
        },
    )
    assert response.status_code == 403


def test_reference_units_readable(client: TestClient) -> None:
    token = _login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    response = client.get("/api/v1/reference/units", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["totalItems"] >= 10


def test_activity_workflow_and_lock(client: TestClient) -> None:
    token_admin = _login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = _org_id(client, token_admin)

    facilities = client.get(
        f"/api/v1/organizations/{org_id}/facilities", headers=_auth(token_admin)
    ).json()["items"]
    facility_id = next(f["id"] for f in facilities if f["code"] == "IZM-PROD")

    types = client.get("/api/v1/reference/activity-types", headers=_auth(token_admin)).json()[
        "items"
    ]
    activity_type_id = next(t["id"] for t in types if t["code"] == "purchased_electricity")

    periods = client.get(
        f"/api/v1/organizations/{org_id}/reporting-periods", headers=_auth(token_admin)
    ).json()["items"]
    period_id = next(p["id"] for p in periods if p["code"] == "2024-01")

    created = client.post(
        f"/api/v1/organizations/{org_id}/activity-records",
        headers=_auth(token_admin),
        json={
            "facilityId": facility_id,
            "activityTypeId": activity_type_id,
            "reportingPeriodId": period_id,
            "activityDate": "2024-01-18",
            "quantity": "100.25",
            "unitCode": "kWh",
            "sourceReference": "INT-TEST-1",
        },
    )
    assert created.status_code == 201, created.text
    record = created.json()
    assert Decimal(record["normalizedQuantity"]) == Decimal("100.2500")

    submitted = client.post(
        f"/api/v1/organizations/{org_id}/activity-records/{record['id']}/submit",
        headers=_auth(token_admin),
        json={"rowVersion": record["rowVersion"], "reason": "ready"},
    )
    assert submitted.status_code == 200, submitted.text
    record = submitted.json()

    approved = client.post(
        f"/api/v1/organizations/{org_id}/activity-records/{record['id']}/approve",
        headers=_auth(token_admin),
        json={"rowVersion": record["rowVersion"], "reason": "ok"},
    )
    assert approved.status_code == 200, approved.text

    locked = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods/{period_id}/lock",
        headers=_auth(token_admin),
    )
    assert locked.status_code == 200, locked.text

    blocked = client.post(
        f"/api/v1/organizations/{org_id}/activity-records",
        headers=_auth(token_admin),
        json={
            "facilityId": facility_id,
            "activityTypeId": activity_type_id,
            "reportingPeriodId": period_id,
            "activityDate": "2024-01-19",
            "quantity": "10",
            "unitCode": "kWh",
        },
    )
    assert blocked.status_code in {400, 409, 422}


def test_csv_template_and_import(client: TestClient) -> None:
    token = _login(client, "analyst@ecotrace.dev", "EcoTraceAnalyst!2024")
    org_id = _org_id(client, token)

    template = client.get(
        f"/api/v1/organizations/{org_id}/imports/activity-records/template",
        headers=_auth(token),
    )
    assert template.status_code == 200
    assert "facilityCode" in template.text

    csv_body = (
        "facilityCode,activityTypeCode,activityDate,quantity,unitCode,reportingPeriodCode,"
        "sourceReference,description\n"
        "IZM-PROD,purchased_electricity,2024-01-22,55.5,kWh,2024-01,CSV-INT-1,Import test\n"
        "UNKNOWN,purchased_electricity,2024-01-23,1,kWh,2024-01,CSV-INT-2,Bad facility\n"
    )
    upload = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records",
        headers=_auth(token),
        files={"file": ("import.csv", csv_body.encode("utf-8"), "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    job_id = upload.json()["id"]

    validated = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records/{job_id}/validate",
        headers=_auth(token),
    )
    assert validated.status_code == 200, validated.text
    body = validated.json()
    assert body["validRows"] == 1
    assert body["invalidRows"] == 1

    executed = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records/{job_id}/execute",
        headers=_auth(token),
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["importedRows"] == 1

    again = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records/{job_id}/execute",
        headers=_auth(token),
    )
    assert again.status_code == 409


def test_seed_idempotent_ops(seeded_db: Session) -> None:
    from ecotrace.db.seed import run_seed

    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    facilities_before = (
        seeded_db.execute(select(Facility).where(Facility.organization_id == org.id))
        .scalars()
        .all()
    )
    run_seed(seeded_db)
    facilities_after = (
        seeded_db.execute(select(Facility).where(Facility.organization_id == org.id))
        .scalars()
        .all()
    )
    assert len(facilities_before) == len(facilities_after)
    assert seeded_db.execute(select(ActivityType)).scalars().first() is not None
    assert seeded_db.execute(select(ReportingPeriod)).scalars().first() is not None
    assert seeded_db.execute(select(ActivityRecord)).scalars().first() is not None
