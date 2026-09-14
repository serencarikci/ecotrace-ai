from __future__ import annotations

import io
import json
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from openpyxl import load_workbook
from tests.cbam_api_profile_helpers import create_published_steel_profile
from tests.helpers import api_login, auth_headers, current_org_id


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f'/api/v1/cbam/organizations/{org_id}'


def _prepare_binding(client: TestClient, token: str, org_id: str) -> tuple[str, str]:
    facilities = client.get(
        f'/api/v1/organizations/{org_id}/facilities', headers=_auth(token)
    ).json()['items']
    inst = client.post(
        f'{_base(org_id)}/installations',
        headers=_auth(token),
        json={
            'facilityId': facilities[0]['id'],
            'code': f'B6-{uuid.uuid4().hex[:8]}',
            'name': 'Export Installation',
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f'/api/v1/organizations/{org_id}/reporting-periods',
        headers=_auth(token),
        json={
            'code': f'B6P-{uuid.uuid4().hex[:6]}',
            'name': 'Export Period',
            'periodType': 'custom',
            'startDate': '2035-01-01',
            'endDate': '2035-03-31',
        },
    )
    assert period.status_code == 201, period.text
    binding = client.post(
        f'{_base(org_id)}/reporting-period-bindings',
        headers=_auth(token),
        json={'reportingPeriodId': period.json()['id']},
    )
    assert binding.status_code == 201, binding.text
    opened = client.post(
        f"{_base(org_id)}/reporting-period-bindings/{binding.json()['id']}/open-data-collection",
        headers=_auth(token),
        json={'rowVersion': binding.json()['rowVersion']},
    )
    assert opened.status_code == 200, opened.text
    return opened.json()['id'], inst.json()['id']


def _seed_ready_period(
    client: TestClient, token: str, org_id: str, binding_id: str, installation_id: str
) -> str:
    profile_id = create_published_steel_profile(client, token, org_id, headers=_auth(token))
    base_prod = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'productProfileVersionId': profile_id,
            'quantity': '500',
            'unit': 't',
        },
    )
    assert base_prod.status_code == 201, base_prod.text
    target_prod = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'productProfileVersionId': profile_id,
            'quantity': '100',
            'unit': 't',
        },
    )
    assert target_prod.status_code == 201, target_prod.text
    activity = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'activityType': 'ELECTRICITY',
            'quantity': '100',
            'unit': 'MWh',
            'dataSourceType': 'PRIMARY',
            'activityDate': '2035-02-01',
        },
    )
    assert activity.status_code == 201, activity.text

    rule = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/allocation-rules',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'allocationMethod': 'PRODUCTION_QUANTITY_RATIO',
            'name': f'Export ratio {uuid.uuid4().hex[:6]}',
            'numeratorProductionRecordId': target_prod.json()['id'],
            'denominatorProductionRecordId': base_prod.json()['id'],
        },
    )
    assert rule.status_code == 201, rule.text
    activated = client.post(
        f"{_base(org_id)}/allocation-rules/{rule.json()['id']}/activate",
        headers=_auth(token),
        json={'rowVersion': rule.json()['rowVersion']},
    )
    assert activated.status_code == 200, activated.text
    alloc = client.post(
        f"{_base(org_id)}/allocation-rules/{activated.json()['id']}/allocate/activity-records/"
        f"{activity.json()['id']}",
        headers=_auth(token),
    )
    assert alloc.status_code == 201, alloc.text
    assert Decimal(alloc.json()['allocatedQuantity']) == Decimal('20.00000000')

    sources = client.get(f'{_base(org_id)}/reference-sources', headers=_auth(token))
    manual = next(s for s in sources.json()['items'] if s['code'] == 'MANUAL_APPROVED_REFERENCE')
    factor_defs = client.get(f'{_base(org_id)}/factor-definitions', headers=_auth(token))
    ef = next(d for d in factor_defs.json()['items'] if d['code'] == 'GENERIC_EMISSION_FACTOR')
    value = client.post(
        f"{_base(org_id)}/factor-definitions/{ef['id']}/values",
        headers=_auth(token),
        json={
            'referenceSourceId': manual['id'],
            'activityType': 'ELECTRICITY',
            'numericValue': '0.4',
            'unit': 'tCO2e/MWh',
            'dataSourceType': 'DEFAULT_REFERENCE',
            'validFrom': '2030-01-01',
            'validUntil': '2040-12-31',
        },
    )
    assert value.status_code == 201, value.text
    activated_value = client.post(
        f"{_base(org_id)}/factor-values/{value.json()['id']}/activate",
        headers=_auth(token),
        json={'rowVersion': value.json()['rowVersion']},
    )
    assert activated_value.status_code == 200, activated_value.text
    resolved = client.post(
        f"{_base(org_id)}/allocation-results/{alloc.json()['id']}/factor-resolutions/"
        f'GENERIC_EMISSION_FACTOR/resolve',
        headers=_auth(token),
    )
    assert resolved.status_code == 201, resolved.text

    defs = client.get(f'{_base(org_id)}/calculation-definitions', headers=_auth(token))
    alloc_def = next(
        d for d in defs.json()['items'] if d['code'] == 'MULTIPLY_ALLOCATION_BY_GENERIC_EF'
    )
    run = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs',
        headers=_auth(token),
        json={},
    )
    assert run.status_code == 201, run.text
    executed = client.post(
        f"{_base(org_id)}/calculation-runs/{run.json()['id']}/execute",
        headers=_auth(token),
        json={'calculationDefinitionIds': [alloc_def['id']]},
    )
    assert executed.status_code == 200, executed.text
    results = client.get(
        f"{_base(org_id)}/calculation-runs/{executed.json()['id']}/results",
        headers=_auth(token),
    )
    assert results.status_code == 200
    calc = next(r for r in results.json()['items'] if r['sourceType'] == 'ALLOCATION_RESULT')
    assert calc['status'] == 'CALCULATED'
    assert Decimal(calc['resultValue']) == Decimal('8.00000000')
    return executed.json()['id']


def test_export_api_permissions_and_flow(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    viewer = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)
    create_published_steel_profile(client, admin, org_id, headers=_auth(admin))

    templates = client.get(f'{_base(org_id)}/export-templates', headers=_auth(viewer))
    assert templates.status_code == 200
    assert templates.json()['totalItems'] >= 1
    template = next(
        t for t in templates.json()['items'] if t['code'] == 'ECOTRACE_SKDM_INTERNAL'
    )
    assert template['templateType'] == 'INTERNAL_SKDM'

    readiness = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/export-readiness',
        headers=_auth(viewer),
    )
    assert readiness.status_code == 200
    assert readiness.json()['status'] == 'NOT_READY'
    assert readiness.json()['officialMappingBlocked'] is True

    summary = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/summary',
        headers=_auth(viewer),
    )
    assert summary.status_code == 200
    assert summary.json()['title'] == 'SKDM Period Summary'

    denied = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/exports',
        headers=_auth(viewer),
        json={},
    )
    assert denied.status_code in {403, 404}

    calc_run_id = _seed_ready_period(client, admin, org_id, binding_id, installation_id)
    ready = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/export-readiness',
        headers=_auth(viewer),
        params={'calculationRunId': calc_run_id},
    )
    assert ready.status_code == 200
    assert ready.json()['status'] == 'READY_WITH_WARNINGS'

    created = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/exports',
        headers=_auth(admin),
        json={
            'exportTemplateId': template['id'],
            'calculationRunId': calc_run_id,
        },
    )
    assert created.status_code == 201, created.text
    export_run = created.json()
    assert export_run['status'] in {'COMPLETED', 'COMPLETED_WITH_WARNINGS'}
    assert export_run['templateVersion'] == template['version']
    assert export_run['calculationRunId'] == calc_run_id

    history = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/exports',
        headers=_auth(viewer),
    )
    assert history.status_code == 200
    assert any(item['id'] == export_run['id'] for item in history.json()['items'])

    artifacts = client.get(
        f"{_base(org_id)}/exports/{export_run['id']}/artifacts",
        headers=_auth(viewer),
    )
    assert artifacts.status_code == 200
    xlsx = next(a for a in artifacts.json() if a['artifactType'] == 'XLSX')
    manifest = next(a for a in artifacts.json() if a['fileName'] == 'export-manifest.json')

    download = client.get(
        f"{_base(org_id)}/export-artifacts/{xlsx['id']}/download",
        headers=_auth(viewer),
    )
    assert download.status_code == 200
    wb = load_workbook(io.BytesIO(download.content))
    assert wb['Summary']['E3'].value == '=COUNTA(A4:A18)'
    assert wb['Calculations']['G3'].value == 8.0
    assert wb['Calculations']['C3'].value == 20.0
    assert wb['Calculations']['E3'].value == 0.4

    manifest_dl = client.get(
        f"{_base(org_id)}/export-artifacts/{manifest['id']}/download",
        headers=_auth(viewer),
    )
    assert manifest_dl.status_code == 200
    payload = json.loads(manifest_dl.content.decode('utf-8'))
    assert payload['calculationRunId'] == calc_run_id
    assert payload['officialMappingBlocked'] is True

    other_org = str(uuid.uuid4())
    cross = client.get(
        f"{_base(other_org)}/export-artifacts/{xlsx['id']}/download",
        headers=_auth(admin),
    )
    assert cross.status_code == 404
    cross_export = client.post(
        f'{_base(other_org)}/reporting-period-bindings/{binding_id}/exports',
        headers=_auth(admin),
        json={},
    )
    assert cross_export.status_code == 404


def test_export_fails_when_not_ready(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, _installation_id = _prepare_binding(client, admin, org_id)
    failed = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/exports',
        headers=_auth(admin),
        json={},
    )
    assert failed.status_code == 422
