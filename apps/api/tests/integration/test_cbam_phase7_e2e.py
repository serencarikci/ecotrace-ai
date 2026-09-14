from __future__ import annotations

import io
import json
import time
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import text
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
            "code": f"B7-{uuid.uuid4().hex[:8]}",
            "name": '=HYPERLINK("http://evil.example")',
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f"/api/v1/organizations/{org_id}/reporting-periods",
        headers=_auth(token),
        json={
            "code": f"B7P-{uuid.uuid4().hex[:6]}",
            "name": "Phase7 Period",
            "periodType": "custom",
            "startDate": "2036-01-01",
            "endDate": "2036-03-31",
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


def _create_factor_and_activate(
    client: TestClient,
    token: str,
    org_id: str,
    *,
    numeric_value: str,
    unit: str,
) -> None:
    sources = client.get(f"{_base(org_id)}/reference-sources", headers=_auth(token))
    manual = next(s for s in sources.json()["items"] if s["code"] == "MANUAL_APPROVED_REFERENCE")
    factor_defs = client.get(f"{_base(org_id)}/factor-definitions", headers=_auth(token))
    ef = next(d for d in factor_defs.json()["items"] if d["code"] == "GENERIC_EMISSION_FACTOR")
    value = client.post(
        f"{_base(org_id)}/factor-definitions/{ef['id']}/values",
        headers=_auth(token),
        json={
            "referenceSourceId": manual["id"],
            "activityType": "ELECTRICITY",
            "numericValue": numeric_value,
            "unit": unit,
            "dataSourceType": "DEFAULT_REFERENCE",
            "validFrom": "2030-01-01",
            "validUntil": "2040-12-31",
        },
    )
    assert value.status_code == 201, value.text
    activated = client.post(
        f"{_base(org_id)}/factor-values/{value.json()['id']}/activate",
        headers=_auth(token),
        json={"rowVersion": value.json()["rowVersion"]},
    )
    assert activated.status_code == 200, activated.text


def test_phase7_positive_end_to_end_mvp_workflow(client: TestClient, engine) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    viewer = api_login(client, "viewer@ecotrace.dev", "EcoTraceViewer!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    profile_id = create_published_steel_profile(client, admin, org_id, headers=_auth(admin))

    denied = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
        headers=_auth(viewer),
        json={
            "installationProfileId": installation_id,
            "quantity": "1",
            "unit": "t",
        },
    )
    assert denied.status_code in {403, 404}

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
            "activityDate": "2036-02-01",
            "notes": '+cmd|"/c calc"',
        },
    )
    assert activity.status_code == 201, activity.text

    rule = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "allocationMethod": "PRODUCTION_QUANTITY_RATIO",
            "name": "Phase7 ratio",
            "numeratorProductionRecordId": target_prod.json()["id"],
            "denominatorProductionRecordId": base_prod.json()["id"],
        },
    )
    assert rule.status_code == 201, rule.text
    assert rule.json()["allocationRatio"] == "0.200000000000"
    activated = client.post(
        f"{_base(org_id)}/allocation-rules/{rule.json()['id']}/activate",
        headers=_auth(admin),
        json={"rowVersion": rule.json()["rowVersion"]},
    )
    assert activated.status_code == 200, activated.text
    alloc = client.post(
        f"{_base(org_id)}/allocation-rules/{activated.json()['id']}/allocate/activity-records/"
        f"{activity.json()['id']}",
        headers=_auth(admin),
    )
    assert alloc.status_code == 201, alloc.text
    assert Decimal(alloc.json()["allocatedQuantity"]) == Decimal("20.00000000")

    _create_factor_and_activate(client, admin, org_id, numeric_value="0.4", unit="tCO2e/MWh")
    resolved = client.post(
        f"{_base(org_id)}/allocation-results/{alloc.json()['id']}/factor-resolutions/"
        f"GENERIC_EMISSION_FACTOR/resolve",
        headers=_auth(admin),
    )
    assert resolved.status_code == 201, resolved.text
    assert resolved.json()["resolutionStatus"] == "RESOLVED_DEFAULT"
    assert Decimal(resolved.json()["selectedValue"]) == Decimal("0.40000000")

    defs = client.get(f"{_base(org_id)}/calculation-definitions", headers=_auth(admin))
    alloc_def = next(
        d for d in defs.json()["items"] if d["code"] == "MULTIPLY_ALLOCATION_BY_GENERIC_EF"
    )
    run = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs",
        headers=_auth(admin),
        json={},
    )
    assert run.status_code == 201, run.text
    executed = client.post(
        f"{_base(org_id)}/calculation-runs/{run.json()['id']}/execute",
        headers=_auth(admin),
        json={"calculationDefinitionIds": [alloc_def["id"]]},
    )
    assert executed.status_code == 200, executed.text
    calc_run_id = executed.json()["id"]
    results = client.get(
        f"{_base(org_id)}/calculation-runs/{calc_run_id}/results",
        headers=_auth(viewer),
    )
    assert results.status_code == 200
    calc = next(r for r in results.json()["items"] if r["sourceType"] == "ALLOCATION_RESULT")
    assert calc["status"] == "CALCULATED"
    assert Decimal(calc["resultValue"]) == Decimal("8.00000000")
    assert calc["resultUnit"] == "tCO2e"

    summary = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/summary",
        headers=_auth(viewer),
    )
    assert summary.status_code == 200
    assert summary.json()["title"] == "SKDM Period Summary"
    assert summary.json()["officialMappingBlocked"] is True

    readiness = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/export-readiness",
        headers=_auth(viewer),
        params={"calculationRunId": calc_run_id},
    )
    assert readiness.status_code == 200
    assert readiness.json()["status"] in {"READY", "READY_WITH_WARNINGS"}
    assert readiness.json()["officialMappingBlocked"] is True

    templates = client.get(f"{_base(org_id)}/export-templates", headers=_auth(viewer))
    template = next(t for t in templates.json()["items"] if t["code"] == "ECOTRACE_SKDM_INTERNAL")
    export = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/exports",
        headers=_auth(admin),
        json={"exportTemplateId": template["id"], "calculationRunId": calc_run_id},
    )
    assert export.status_code == 201, export.text
    export_run_id = export.json()["id"]
    artifacts = client.get(
        f"{_base(org_id)}/exports/{export_run_id}/artifacts",
        headers=_auth(viewer),
    )
    assert artifacts.status_code == 200
    xlsx = next(a for a in artifacts.json() if a["artifactType"] == "XLSX")
    manifest = next(a for a in artifacts.json() if a["fileName"] == "export-manifest.json")

    download = client.get(
        f"{_base(org_id)}/export-artifacts/{xlsx['id']}/download",
        headers=_auth(viewer),
    )
    assert download.status_code == 200
    wb = load_workbook(io.BytesIO(download.content))
    assert "INTERNAL DEVELOPMENT TEMPLATE" in str(wb["Organization"]["A1"].value)
    assert wb["Summary"]["E3"].value == "=COUNTA(A4:A18)"
    assert wb["Calculations"]["C3"].value == 20.0
    assert wb["Calculations"]["E3"].value == 0.4
    assert wb["Calculations"]["G3"].value == 8.0
    assert wb["Installation"]["B4"].value == '\'=HYPERLINK("http://evil.example")'

    manifest_dl = client.get(
        f"{_base(org_id)}/export-artifacts/{manifest['id']}/download",
        headers=_auth(viewer),
    )
    payload = json.loads(manifest_dl.content.decode("utf-8"))
    assert payload["calculationRunId"] == calc_run_id
    assert payload["officialMappingBlocked"] is True
    assert payload["traceability"]["calculationResultIds"]
    assert payload["artifactChecksum"] == xlsx["sha256"]

    with engine.connect() as conn:
        actions = {
            row[0]
            for row in conn.execute(
                text(
                    """
                    SELECT action FROM audit_logs
                    WHERE organization_id = CAST(:org AS uuid)
                      AND action LIKE 'cbam.%'
                    """
                ),
                {"org": org_id},
            )
        }
    for required in {
        "cbam.installation.created",
        "cbam.period_binding.created",
        "cbam.production_record.created",
        "cbam.activity_record.created",
        "cbam.allocation_rule.created",
        "cbam.allocation.executed",
        "cbam.factor_resolution.resolved",
        "cbam.calculation_run.created",
        "cbam.calculation_run.executed",
        "cbam.export.generated",
        "cbam.export.downloaded",
    }:
        assert required in actions, f"missing audit action {required}"


def test_phase7_negative_unresolved_factor(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    create_published_steel_profile(client, admin, org_id, headers=_auth(admin))
    activity = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "activityType": "ELECTRICITY",
            "quantity": "10",
            "unit": "kWh",
            "dataSourceType": "PRIMARY",
            "activityDate": "2036-02-01",
        },
    )
    assert activity.status_code == 201
    resolved = client.post(
        f"{_base(org_id)}/activity-records/{activity.json()['id']}"
        f"/factor-resolutions/GENERIC_EMISSION_FACTOR/resolve",
        headers=_auth(admin),
        json={},
    )
    assert resolved.status_code in {200, 201}
    assert resolved.json()["resolutionStatus"] == "UNRESOLVED"
    run = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs",
        headers=_auth(admin),
        json={},
    )
    executed = client.post(
        f"{_base(org_id)}/calculation-runs/{run.json()['id']}/execute",
        headers=_auth(admin),
        json={"allowUnallocatedActivity": True},
    )
    assert executed.status_code == 200
    results = client.get(
        f"{_base(org_id)}/calculation-runs/{executed.json()['id']}/results",
        headers=_auth(admin),
    ).json()["items"]
    blocked = [r for r in results if r["sourceId"] == activity.json()["id"]]
    assert blocked
    assert all(r.get("resultValue") in (None, "") for r in blocked)
    readiness = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/export-readiness",
        headers=_auth(admin),
        params={"calculationRunId": executed.json()["id"]},
    )
    assert readiness.json()["status"] == "NOT_READY"


def test_phase7_negative_ambiguous_factor(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    create_published_steel_profile(client, admin, org_id, headers=_auth(admin))
    activity = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "activityType": "ELECTRICITY",
            "quantity": "10",
            "unit": "kWh",
            "dataSourceType": "PRIMARY",
            "activityDate": "2036-02-01",
        },
    )
    assert activity.status_code == 201
    _create_factor_and_activate(client, admin, org_id, numeric_value="0.4", unit="kgCO2e/kWh")
    _create_factor_and_activate(client, admin, org_id, numeric_value="0.5", unit="kgCO2e/kWh")
    resolved = client.post(
        f"{_base(org_id)}/activity-records/{activity.json()['id']}"
        f"/factor-resolutions/GENERIC_EMISSION_FACTOR/resolve",
        headers=_auth(admin),
        json={},
    )
    assert resolved.json()["resolutionStatus"] == "AMBIGUOUS"
    run = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs",
        headers=_auth(admin),
        json={},
    )
    executed = client.post(
        f"{_base(org_id)}/calculation-runs/{run.json()['id']}/execute",
        headers=_auth(admin),
        json={"allowUnallocatedActivity": True},
    )
    results = client.get(
        f"{_base(org_id)}/calculation-runs/{executed.json()['id']}/results",
        headers=_auth(admin),
    ).json()["items"]
    assert any(
        r["sourceId"] == activity.json()["id"] and r["status"] == "AMBIGUOUS_FACTOR"
        for r in results
    )


def test_phase7_negative_incompatible_unit(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    create_published_steel_profile(client, admin, org_id, headers=_auth(admin))
    activity = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "activityType": "ELECTRICITY",
            "quantity": "100",
            "unit": "kWh",
            "dataSourceType": "PRIMARY",
            "activityDate": "2036-02-01",
        },
    )
    assert activity.status_code == 201, activity.text
    _create_factor_and_activate(client, admin, org_id, numeric_value="0.4", unit="kgCO2e/L")
    resolved = client.post(
        f"{_base(org_id)}/activity-records/{activity.json()['id']}"
        f"/factor-resolutions/GENERIC_EMISSION_FACTOR/resolve",
        headers=_auth(admin),
        json={},
    )
    assert resolved.status_code in {200, 201}
    run = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs",
        headers=_auth(admin),
        json={},
    )
    executed = client.post(
        f"{_base(org_id)}/calculation-runs/{run.json()['id']}/execute",
        headers=_auth(admin),
        json={"allowUnallocatedActivity": True},
    )
    assert executed.status_code == 200
    results = client.get(
        f"{_base(org_id)}/calculation-runs/{executed.json()['id']}/results",
        headers=_auth(admin),
    ).json()["items"]
    activity_results = [r for r in results if r["sourceId"] == activity.json()["id"]]
    assert activity_results
    assert any(r["status"] == "INCOMPATIBLE_UNIT" for r in activity_results)
    assert all(r.get("resultValue") in (None, "") for r in activity_results)


def test_phase7_negative_cross_tenant_and_stale_version(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    profile_id = create_published_steel_profile(client, admin, org_id, headers=_auth(admin))
    prod = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "productProfileVersionId": profile_id,
            "quantity": "10",
            "unit": "t",
        },
    )
    assert prod.status_code == 201
    other_org = str(uuid.uuid4())
    for path in (
        f"{_base(other_org)}/installations/{installation_id}",
        f"{_base(other_org)}/reporting-period-bindings/{binding_id}",
        f"{_base(other_org)}/production-records/{prod.json()['id']}",
        f"{_base(other_org)}/reporting-period-bindings/{binding_id}/exports",
    ):
        response = client.get(path, headers=_auth(admin))
        if response.status_code == 405:
            response = client.post(path, headers=_auth(admin), json={})
        assert response.status_code == 404, path

    stale = client.post(
        f"{_base(org_id)}/production-records/{prod.json()['id']}/archive",
        headers=_auth(admin),
        json={"rowVersion": 999},
    )
    assert stale.status_code == 409


def test_phase7_negative_purchased_missing_consumed(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    create_published_steel_profile(client, admin, org_id, headers=_auth(admin))
    purchased = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/purchased-inputs",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "inputName": "Precursor",
            "quantity": "50",
            "unit": "t",
        },
    )
    assert purchased.status_code == 201, purchased.text
    rule = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules",
        headers=_auth(admin),
        json={
            "installationProfileId": installation_id,
            "allocationMethod": "DIRECT_ASSIGNMENT",
            "name": "Purchased direct",
        },
    )
    assert rule.status_code == 201
    activated = client.post(
        f"{_base(org_id)}/allocation-rules/{rule.json()['id']}/activate",
        headers=_auth(admin),
        json={"rowVersion": rule.json()["rowVersion"]},
    )
    assert activated.status_code == 200
    alloc = client.post(
        f"{_base(org_id)}/allocation-rules/{activated.json()['id']}/allocate/purchased-inputs/"
        f"{purchased.json()['id']}",
        headers=_auth(admin),
    )
    assert alloc.status_code in {400, 409, 422}


def test_phase7_performance_sanity_list_and_summary(client: TestClient) -> None:
    admin = api_login(client, "orgadmin@ecotrace.dev", "EcoTraceOrgAdmin!2024")
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    profile_id = create_published_steel_profile(client, admin, org_id, headers=_auth(admin))

    for i in range(25):
        created = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records",
            headers=_auth(admin),
            json={
                "installationProfileId": installation_id,
                "productProfileVersionId": profile_id,
                "quantity": str(i + 1),
                "unit": "t",
            },
        )
        assert created.status_code == 201
    for _ in range(80):
        created = client.post(
            f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
            headers=_auth(admin),
            json={
                "installationProfileId": installation_id,
                "activityType": "ELECTRICITY",
                "quantity": "1",
                "unit": "kWh",
                "dataSourceType": "PRIMARY",
                "activityDate": "2036-02-01",
            },
        )
        assert created.status_code == 201

    started = time.perf_counter()
    listed = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records",
        headers=_auth(admin),
        params={"page": 1, "pageSize": 50},
    )
    list_ms = (time.perf_counter() - started) * 1000
    assert listed.status_code == 200
    assert listed.json()["totalItems"] >= 80

    started = time.perf_counter()
    summary = client.get(
        f"{_base(org_id)}/reporting-period-bindings/{binding_id}/summary",
        headers=_auth(admin),
    )
    summary_ms = (time.perf_counter() - started) * 1000
    assert summary.status_code == 200
    assert list_ms < 5000
    assert summary_ms < 5000
