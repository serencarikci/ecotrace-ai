from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
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
            'code': f'B5-{uuid.uuid4().hex[:8]}',
            'name': 'Calc Installation',
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f'/api/v1/organizations/{org_id}/reporting-periods',
        headers=_auth(token),
        json={
            'code': f'B5P-{uuid.uuid4().hex[:6]}',
            'name': 'Calc Period',
            'periodType': 'custom',
            'startDate': '2033-01-01',
            'endDate': '2033-03-31',
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


def test_calculation_api_flow(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    viewer = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    org_id = current_org_id(client, admin)
    binding_id, installation_id = _prepare_binding(client, admin, org_id)

    defs = client.get(f'{_base(org_id)}/calculation-definitions', headers=_auth(viewer))
    assert defs.status_code == 200
    assert defs.json()['totalItems'] >= 1

    denied = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs',
        headers=_auth(viewer),
        json={},
    )
    assert denied.status_code in {403, 404}

    sources = client.get(f'{_base(org_id)}/reference-sources', headers=_auth(admin))
    assert sources.status_code == 200
    manual = next(s for s in sources.json()['items'] if s['code'] == 'MANUAL_APPROVED_REFERENCE')
    factor_defs = client.get(f'{_base(org_id)}/factor-definitions', headers=_auth(admin))
    ef = next(d for d in factor_defs.json()['items'] if d['code'] == 'GENERIC_EMISSION_FACTOR')

    activity = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records',
        headers=_auth(admin),
        json={
            'installationProfileId': installation_id,
            'activityType': 'ELECTRICITY',
            'quantity': '100',
            'unit': 'kWh',
            'dataSourceType': 'PRIMARY',
            'activityDate': '2033-02-01',
        },
    )
    assert activity.status_code == 201, activity.text

    value = client.post(
        f"{_base(org_id)}/factor-definitions/{ef['id']}/values",
        headers=_auth(admin),
        json={
            'referenceSourceId': manual['id'],
            'activityType': 'ELECTRICITY',
            'numericValue': '0.5',
            'unit': 'kgCO2e/kWh',
            'dataSourceType': 'DEFAULT_REFERENCE',
            'validFrom': '2030-01-01',
            'validUntil': '2040-12-31',
        },
    )
    assert value.status_code == 201, value.text
    activated = client.post(
        f"{_base(org_id)}/factor-values/{value.json()['id']}/activate",
        headers=_auth(admin),
        json={'rowVersion': value.json()['rowVersion']},
    )
    assert activated.status_code == 200, activated.text

    resolved = client.post(
        f"{_base(org_id)}/activity-records/{activity.json()['id']}"
        f"/factor-resolutions/GENERIC_EMISSION_FACTOR/resolve",
        headers=_auth(admin),
        json={},
    )
    assert resolved.status_code in {200, 201}, resolved.text
    assert resolved.json()['resolutionStatus'] == 'RESOLVED_DEFAULT'

    created_run = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/calculation-runs',
        headers=_auth(admin),
        json={},
    )
    assert created_run.status_code == 201, created_run.text
    run_id = created_run.json()['id']

    executed = client.post(
        f'{_base(org_id)}/calculation-runs/{run_id}/execute',
        headers=_auth(admin),
        json={'allowUnallocatedActivity': True},
    )
    assert executed.status_code == 200, executed.text
    body = executed.json()
    assert body['calculatedCount'] >= 1
    assert body['status'] in {'COMPLETED', 'PARTIALLY_COMPLETED'}

    results = client.get(
        f'{_base(org_id)}/calculation-runs/{run_id}/results',
        headers=_auth(viewer),
    )
    assert results.status_code == 200
    items = results.json()['items']
    assert any(
        i['status'] == 'CALCULATED'
        and Decimal(i['resultValue']) == Decimal('50.00000000')
        and i['resultUnit'] == 'kgCO2e'
        for i in items
    )
    result_id = next(i['id'] for i in items if i['status'] == 'CALCULATED')

    recalc = client.post(
        f'{_base(org_id)}/calculation-results/{result_id}/recalculate',
        headers=_auth(admin),
    )
    assert recalc.status_code == 200, recalc.text
    assert recalc.json()['id'] != result_id
