"""Phase 10C product embedded-emissions roll-up HTTP API contract tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from tests.cbam_api_profile_helpers import create_published_steel_profile
from tests.helpers import api_login, auth_headers, current_org_id

ACTIVITY_DAY = '2024-07-15'
MONTH_START = '2024-07-01'
TOTAL_PRODUCTION = '100'
CBAM_PRODUCTION = '10'
PRECURSOR_USE = '3'


def _auth(token: str) -> dict[str, str]:
    return auth_headers(token)


def _base(org_id: str) -> str:
    return f'/api/v1/cbam/organizations/{org_id}'


def _pee(org_id: str, binding_id: str) -> str:
    return (
        f'{_base(org_id)}/reporting-period-bindings/{binding_id}/product-embedded-emissions'
    )


def _binding(org_id: str, binding_id: str) -> str:
    return f'{_base(org_id)}/reporting-period-bindings/{binding_id}'


def _prepare_binding(client: TestClient, token: str, org_id: str) -> tuple[str, str]:
    facilities = client.get(
        f'/api/v1/organizations/{org_id}/facilities', headers=_auth(token)
    ).json()['items']
    inst = client.post(
        f'{_base(org_id)}/installations',
        headers=_auth(token),
        json={
            'facilityId': facilities[0]['id'],
            'code': f'PEE-{uuid.uuid4().hex[:8]}',
            'name': 'Roll-up API Installation',
        },
    )
    assert inst.status_code == 201, inst.text
    period = client.post(
        f'/api/v1/organizations/{org_id}/reporting-periods',
        headers=_auth(token),
        json={
            'code': f'PEEP-{uuid.uuid4().hex[:6]}',
            'name': 'Roll-up API Period',
            'periodType': 'custom',
            'startDate': MONTH_START,
            'endDate': '2024-07-31',
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


def seed_ready_rollup(client: TestClient, token: str, org_id: str) -> tuple[str, str, str]:
    """Return (bindingId, installationId, productProfileVersionId) ready for roll-up."""
    binding_id, installation_id = _prepare_binding(client, token, org_id)

    gas = client.post(
        f'{_binding(org_id, binding_id)}/activity-records',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'activityType': 'NATURAL_GAS',
            'quantity': '188',
            'unit': 'Sm3',
            'dataSourceType': 'PRIMARY',
            'activityDate': ACTIVITY_DAY,
        },
    )
    assert gas.status_code == 201, gas.text
    sc = client.post(
        f'{_binding(org_id, binding_id)}/stationary-combustion/executions',
        headers=_auth(token),
        json={
            'clientRequestId': str(uuid.uuid4()),
            'activityRecordId': gas.json()['id'],
            'fuelCode': 'NATURAL_GAS',
            'densityValue': '0.68',
            'densityUnit': 'kg/Sm3',
        },
    )
    assert sc.status_code == 201, sc.text

    electricity = client.post(
        f'{_binding(org_id, binding_id)}/activity-records',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'activityType': 'ELECTRICITY',
            'quantity': '176034.53',
            'unit': 'kWh',
            'dataSourceType': 'PRIMARY',
            'activityDate': ACTIVITY_DAY,
        },
    )
    assert electricity.status_code == 201, electricity.text
    pe = client.post(
        f'{_binding(org_id, binding_id)}/purchased-electricity/executions',
        headers=_auth(token),
        json={
            'clientRequestId': str(uuid.uuid4()),
            'activityRecordId': electricity.json()['id'],
            'factorSourceMode': 'MANUAL',
            'manualFactor': {
                'value': '0.439',
                'unit': 'tCO2e/MWh',
                'sourceName': 'Workbook H4',
                'sourceDocument': 'SKDM_Alokasyon_Sablon.xlsx',
                'datasetVersion': 'workbook-example',
                'referenceDescription': 'Example EF',
                'effectiveDate': '2024-01-01',
            },
        },
    )
    assert pe.status_code == 201, pe.text

    basis = client.post(
        f'{_binding(org_id, binding_id)}/monthly-production-basis',
        headers=_auth(token),
        json={
            'monthStart': MONTH_START,
            'totalProductionQuantity': TOTAL_PRODUCTION,
            'cbamQuantity': CBAM_PRODUCTION,
            'quantityUnit': 't',
        },
    )
    assert basis.status_code == 201, basis.text

    profile_id = create_published_steel_profile(client, token, org_id, headers=_auth(token))
    production = client.post(
        f'{_binding(org_id, binding_id)}/production-records',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'productProfileVersionId': profile_id,
            'quantity': CBAM_PRODUCTION,
            'unit': 't',
            'productionDate': ACTIVITY_DAY,
        },
    )
    assert production.status_code == 201, production.text

    for path in ('direct-emissions-allocation', 'indirect-emissions-allocation'):
        run = client.post(
            f'{_binding(org_id, binding_id)}/{path}/executions',
            headers=_auth(token),
            json={'clientRequestId': str(uuid.uuid4())},
        )
        assert run.status_code == 201, run.text

    process = client.post(
        f'{_binding(org_id, binding_id)}/production-processes',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'name': 'Roll-up process',
            'productProfileVersionId': profile_id,
            'producedQuantity': CBAM_PRODUCTION,
            'producedQuantityUnit': 't',
            'marketedQuantity': CBAM_PRODUCTION,
            'marketedQuantityUnit': 't',
            'nonCbamQuantity': '0',
            'nonCbamQuantityUnit': 't',
            'hasMeasurableHeat': False,
            'hasWasteGas': False,
        },
    )
    assert process.status_code == 201, process.text

    precursor = client.post(
        f'{_binding(org_id, binding_id)}/purchased-precursors',
        headers=_auth(token),
        json={
            'installationProfileId': installation_id,
            'dataSourceMode': 'SUPPLIER_DATA',
            'name': 'Golden precursor',
            'quantity': '5',
            'quantityUnit': 't',
            'nonCbamQuantity': '2',
            'nonCbamQuantityUnit': 't',
            'specificDirectEmbeddedEmissions': '0.5',
            'electricityConsumptionIntensity': '0.2',
            'electricityEmissionFactor': '0.5',
            'provenanceNotes': 'Supplier declaration 2024-07',
        },
    )
    assert precursor.status_code == 201, precursor.text
    use = client.post(
        f"{_binding(org_id, binding_id)}/purchased-precursors/{precursor.json()['id']}"
        f'/product-uses',
        headers=_auth(token),
        json={
            'targetProductProfileVersionId': profile_id,
            'quantity': PRECURSOR_USE,
            'unit': 't',
        },
    )
    assert use.status_code == 201, use.text
    return binding_id, installation_id, profile_id


def test_readiness_execute_replay_list_detail_summary(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, _, profile_id = seed_ready_rollup(client, admin, org_id)

    ready = client.get(f'{_pee(org_id, binding_id)}/readiness', headers=_auth(admin))
    assert ready.status_code == 200, ready.text
    body = ready.json()
    assert body['rollupReady'] is True
    assert body['status'] == 'READY'
    assert body['blockingIssueCodes'] == []
    assert body['eligibleProductCount'] == 1
    assert body['precursorContributionCount'] == 1
    assert body['products'][0]['productProfileVersionId'] == profile_id
    assert body['exportedElectricityNoteCode'] == (
        'PROCESS_LEVEL_EXPORTED_ELECTRICITY_MODELED'
    )
    assert body['internalPrecursorNoteCode'] == (
        'INTERNAL_PROCESS_PRECURSOR_LEONTIEF_MODELED'
    )

    client_id = str(uuid.uuid4())
    first = client.post(
        f'{_pee(org_id, binding_id)}/executions',
        headers=_auth(admin),
        json={'clientRequestId': client_id},
    )
    assert first.status_code == 201, first.text
    created = first.json()
    assert created['idempotentReplay'] is False
    assert created['status'] == 'COMPLETED'
    assert created['productCount'] == 1
    assert created['resultUnit'] == 'tCO2e'
    assert created['specificUnit'] == 'tCO2e/t'
    assert isinstance(created['totalEmbeddedTco2e'], str)

    replay = client.post(
        f'{_pee(org_id, binding_id)}/executions',
        headers=_auth(admin),
        json={'clientRequestId': client_id},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()['idempotentReplay'] is True
    assert replay.json()['resultId'] == created['resultId']

    listing = client.get(f'{_pee(org_id, binding_id)}/results', headers=_auth(admin))
    assert listing.status_code == 200
    assert listing.json()['totalItems'] == 1
    assert listing.json()['items'][0]['isCurrent'] is True
    assert listing.json()['items'][0]['isStale'] is False

    detail = client.get(
        f"{_pee(org_id, binding_id)}/results/{created['resultId']}", headers=_auth(admin)
    )
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert d['isCurrent'] is True
    assert d['isStale'] is False
    assert d['workbookSha256']
    assert d['deaSourceUnit'] == 'tCO2'
    assert d['workbookGwp'] == '1'
    assert len(d['products']) == 1
    assert len(d['precursorContributions']) == 1

    product = d['products'][0]
    assert Decimal(product['precursorDirectTco2eRaw']) == Decimal('1.5')
    assert Decimal(product['precursorIndirectTco2eRaw']) == Decimal('0.3')
    assert Decimal(product['exportedElectricityDirectTco2e']) == Decimal('0')
    assert Decimal(product['totalEmbeddedTco2eRaw']) == Decimal(
        product['totalDirectTco2eRaw']
    ) + Decimal(product['totalIndirectTco2eRaw'])
    assert Decimal(product['specificTotalRaw']) == Decimal(
        product['totalEmbeddedTco2eRaw']
    ) / Decimal(product['denominatorTonnes'])

    summary = client.get(f'{_pee(org_id, binding_id)}/summary', headers=_auth(admin))
    assert summary.status_code == 200, summary.text
    assert summary.json()['currentResultId'] == created['resultId']
    assert summary.json()['currentIsStale'] is False
    assert len(summary.json()['totalsByProduct']) == 1


def test_execution_rejects_client_supplied_totals(client: TestClient) -> None:
    """The request body carries an idempotency key only; totals are server-authoritative."""
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, _, _ = seed_ready_rollup(client, admin, org_id)

    response = client.post(
        f'{_pee(org_id, binding_id)}/executions',
        headers=_auth(admin),
        json={
            'clientRequestId': str(uuid.uuid4()),
            'totalEmbeddedTco2e': '999',
            'specificTotal': '999',
        },
    )
    assert response.status_code == 422, response.text


def test_viewer_can_read_but_not_execute(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, _, _ = seed_ready_rollup(client, admin, org_id)
    viewer = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')

    assert (
        client.get(f'{_pee(org_id, binding_id)}/readiness', headers=_auth(viewer)).status_code
        == 200
    )
    assert (
        client.get(f'{_pee(org_id, binding_id)}/summary', headers=_auth(viewer)).status_code
        == 200
    )
    denied = client.post(
        f'{_pee(org_id, binding_id)}/executions',
        headers=_auth(viewer),
        json={'clientRequestId': str(uuid.uuid4())},
    )
    assert denied.status_code in (403, 404)


def test_execution_is_blocked_when_nothing_is_ready(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, _ = _prepare_binding(client, admin, org_id)

    ready = client.get(f'{_pee(org_id, binding_id)}/readiness', headers=_auth(admin))
    assert ready.status_code == 200
    assert ready.json()['rollupReady'] is False
    assert 'PRODUCT_EMBEDDED_EMISSIONS_NO_ELIGIBLE_PRODUCTS' in (
        ready.json()['blockingIssueCodes']
    )

    blocked = client.post(
        f'{_pee(org_id, binding_id)}/executions',
        headers=_auth(admin),
        json={'clientRequestId': str(uuid.uuid4())},
    )
    assert blocked.status_code == 400, blocked.text
    assert {d['code'] for d in blocked.json()['error']['details']} >= {
        'DIRECT_EMISSIONS_ALLOCATION_NOT_READY',
        'INDIRECT_EMISSIONS_ALLOCATION_NOT_READY',
        'PRODUCT_EMBEDDED_EMISSIONS_NO_ELIGIBLE_PRODUCTS',
    }

    summary = client.get(f'{_pee(org_id, binding_id)}/summary', headers=_auth(admin))
    assert summary.status_code == 200
    assert summary.json()['currentResultId'] is None


def test_unknown_result_returns_404(client: TestClient) -> None:
    admin = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, admin)
    binding_id, _, _ = seed_ready_rollup(client, admin, org_id)

    missing = client.get(
        f'{_pee(org_id, binding_id)}/results/{uuid.uuid4()}', headers=_auth(admin)
    )
    assert missing.status_code == 404
