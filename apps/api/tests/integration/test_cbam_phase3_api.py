from __future__ import annotations

import uuid

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
            'code': f'P3I-{uuid.uuid4().hex[:8]}',
            'name': 'P3 API Inst',
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f'/api/v1/organizations/{org_id}/reporting-periods',
        headers=_auth(token),
        json={
            'code': f'P3P-{uuid.uuid4().hex[:6]}',
            'name': 'P3 API Period',
            'periodType': 'custom',
            'startDate': '2029-01-01',
            'endDate': '2029-03-31',
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


def test_catalogs_and_data_collection_flow(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    viewer = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    org_id = current_org_id(client, admin)
    types = client.get(f'{_base(org_id)}/activity-types', headers=_auth(viewer))
    assert types.status_code == 200
    assert any(t['code'] == 'ELECTRICITY' for t in types.json())
    units = client.get(f'{_base(org_id)}/units', headers=_auth(viewer))
    assert units.status_code == 200
    assert any(u['code'] == 'kWh' for u in units.json())

    binding_id, installation_id = _prepare_binding(client, admin, org_id)

    denied = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records',
        headers=_auth(viewer),
        json={
            'installationProfileId': installation_id,
            'quantity': '10',
            'unit': 't',
        },
    )
    assert denied.status_code == 403

    created = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records',
        headers=_auth(admin),
        json={
            'installationProfileId': installation_id,
            'quantity': '10',
            'unit': 't',
            'notes': 'batch',
        },
    )
    assert created.status_code == 201, created.text
    record_id = created.json()['id']

    listed = client.get(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/production-records',
        headers=_auth(viewer),
    )
    assert listed.status_code == 200
    assert listed.json()['totalItems'] >= 1

    stale = client.patch(
        f'{_base(org_id)}/production-records/{record_id}',
        headers=_auth(admin),
        json={'rowVersion': 99, 'notes': 'stale'},
    )
    assert stale.status_code == 409

    activity = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records',
        headers=_auth(admin),
        json={
            'installationProfileId': installation_id,
            'activityType': 'ELECTRICITY',
            'quantity': '12500',
            'unit': 'kWh',
            'dataSourceType': 'PRIMARY',
            'sourceReference': 'meter-A',
        },
    )
    assert activity.status_code == 201, activity.text

    bad_unit = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/activity-records',
        headers=_auth(admin),
        json={
            'installationProfileId': installation_id,
            'activityType': 'ELECTRICITY',
            'quantity': '1',
            'unit': 'L',
            'dataSourceType': 'UNKNOWN',
        },
    )
    assert bad_unit.status_code == 422

    purchased = client.post(
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/purchased-inputs',
        headers=_auth(admin),
        json={
            'installationProfileId': installation_id,
            'inputName': 'Precursor X',
            'quantity': '100',
            'unit': 't',
            'consumedQuantity': '40',
            'consumedUnit': 't',
            'embeddedEmissionSourceType': 'NOT_PROVIDED',
        },
    )
    assert purchased.status_code == 201, purchased.text

    archived = client.post(
        f'{_base(org_id)}/production-records/{record_id}/archive',
        headers=_auth(admin),
        json={'rowVersion': created.json()['rowVersion']},
    )
    assert archived.status_code == 200
    assert archived.json()['status'] == 'archived'
