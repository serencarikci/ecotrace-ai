from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.organizations.infrastructure.models import (
    Organization,
)
from helpers import api_login as _login


def test_facility_cross_org_returns_404(client: TestClient, engine) -> None:
    token = _login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    headers = {"Authorization": f"Bearer {token}"}

    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db: Session = session_factory()
    try:
        db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()
        other = Organization(
            id=uuid.uuid4(),
            name="Other Org",
            slug="other-org-isolation",
            country_code="US",
            timezone="UTC",
            is_active=True,
        )
        db.add(other)
        db.flush()
        from ecotrace.modules.facilities.infrastructure.models import Facility

        facility = Facility(
            organization_id=other.id,
            code="OTHER-1",
            name="Hidden Facility",
            facility_type="office",
            country_code="US",
            timezone="UTC",
            is_active=True,
        )
        db.add(facility)
        db.commit()
        other_id = other.id
        facility_id = facility.id
    finally:
        db.close()

    response = client.get(
        f"/api/v1/organizations/{other_id}/facilities/{facility_id}",
        headers=headers,
    )
    assert response.status_code == 404

    response = client.get(
        f"/api/v1/organizations/{other_id}/facilities",
        headers=headers,
    )
    assert response.status_code == 404


def test_period_lock_and_csv_validation(client: TestClient) -> None:
    token = _login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    headers = {"Authorization": f"Bearer {token}"}

    orgs = client.get("/api/v1/organizations", headers=headers)
    assert orgs.status_code == 200
    org_id = orgs.json()["items"][0]["id"]

    periods = client.get(f"/api/v1/organizations/{org_id}/reporting-periods", headers=headers)
    assert periods.status_code == 200
    period = next(p for p in periods.json()["items"] if p["code"] == "2024-01")

    lock = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods/{period['id']}/lock",
        headers=headers,
    )
    assert lock.status_code == 200
    assert lock.json()["status"] == "locked"

    unlock = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods/{period['id']}/unlock",
        headers=headers,
    )
    assert unlock.status_code == 200
    assert unlock.json()["status"] == "open"

    bad_csv = b"facilityCode,quantity\nIZM-PROD,10\n"
    upload = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records",
        headers=headers,
        files={"file": ("bad.csv", bad_csv, "text/csv")},
    )
    assert upload.status_code == 422

    template = client.get(
        f"/api/v1/organizations/{org_id}/imports/activity-records/template",
        headers=headers,
    )
    assert template.status_code == 200
    assert "facilityCode" in template.text

    good_csv = (
        b"facilityCode,activityTypeCode,activityDate,quantity,unitCode,reportingPeriodCode\n"
        b"IZM-PROD,purchased_electricity,2024-01-10,100,kWh,2024-01\n"
    )
    job = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records",
        headers=headers,
        files={"file": ("good.csv", good_csv, "text/csv")},
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]

    validated = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records/{job_id}/validate",
        headers=headers,
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["validRows"] == 1
    assert validated.json()["status"] == "ready"

    executed = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records/{job_id}/execute",
        headers=headers,
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["importedRows"] == 1

    again = client.post(
        f"/api/v1/organizations/{org_id}/imports/activity-records/{job_id}/execute",
        headers=headers,
    )
    assert again.status_code == 409


def test_reference_units_list(client: TestClient) -> None:
    token = _login(client, "analyst@ecotrace.dev", "EcoTraceAnalyst!2024")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/reference/units?pageSize=50", headers=headers)
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["items"]}
    assert "kWh" in codes
    assert "MWh" in codes
