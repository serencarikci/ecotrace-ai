from __future__ import annotations
from decimal import Decimal
from fastapi.testclient import TestClient
from ecotrace.modules.analytics.application.query_service import compute_target_progress
from tests.helpers import api_login, auth_headers, current_org_id

def test_compute_target_progress_on_track() -> None:
    result = compute_target_progress(Decimal('100'), Decimal('70'), Decimal('50'), direction='decrease', elapsed_ratio=Decimal('0.5'))
    assert result['status'] == 'on_track'
    assert Decimal(result['progressPercentage']) == Decimal('60')

def test_compute_target_progress_off_track() -> None:
    result = compute_target_progress(Decimal('100'), Decimal('95'), Decimal('50'), direction='decrease', elapsed_ratio=Decimal('0.8'))
    assert result['status'] == 'off_track'

def test_compute_target_progress_achieved() -> None:
    result = compute_target_progress(Decimal('100'), Decimal('40'), Decimal('50'), direction='decrease', elapsed_ratio=Decimal('0.5'))
    assert result['status'] == 'achieved'

def test_compute_target_progress_unavailable() -> None:
    result = compute_target_progress(Decimal('100'), None, Decimal('50'), direction='decrease', elapsed_ratio=Decimal('0.5'))
    assert result['status'] == 'unavailable'

def test_analytics_dashboard_approved_inventory(client: TestClient) -> None:
    token = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    org_id = current_org_id(client, token)
    response = client.get(f'/api/v1/organizations/{org_id}/analytics/dashboard', headers=auth_headers(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['metadata']['provisional'] is False
    assert body['metadata']['inventoryStatus'] == 'approved'
    assert 'totalEmissionsKgCo2e' in body['summary']

def test_analytics_org_isolation(client: TestClient) -> None:
    token = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    fake_org = '00000000-0000-0000-0000-000000000099'
    response = client.get(f'/api/v1/organizations/{fake_org}/analytics/dashboard', headers=auth_headers(token))
    assert response.status_code in {403, 404}

def test_scenario_calculate_does_not_mutate_activities(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    before = client.get(f'/api/v1/organizations/{org_id}/activity-records', params={'pageSize': 100}, headers=auth_headers(token))
    assert before.status_code == 200, before.text
    before_items = {(row['id'], row['quantity'], row.get('rowVersion')) for row in before.json()['items']}
    scenarios = client.get(f'/api/v1/organizations/{org_id}/scenarios', headers=auth_headers(token))
    assert scenarios.status_code == 200, scenarios.text
    items = scenarios.json()['items']
    assert items
    scenario_id = items[0]['id']
    calc = client.post(f'/api/v1/organizations/{org_id}/scenarios/{scenario_id}/calculate', headers=auth_headers(token))
    assert calc.status_code == 200, calc.text
    after = client.get(f'/api/v1/organizations/{org_id}/activity-records', params={'pageSize': 100}, headers=auth_headers(token))
    assert after.status_code == 200, after.text
    after_items = {(row['id'], row['quantity'], row.get('rowVersion')) for row in after.json()['items']}
    assert before_items == after_items

def test_target_progress_endpoint(client: TestClient) -> None:
    token = api_login(client, 'analyst@ecotrace.dev', 'EcoTraceAnalyst!2024')
    org_id = current_org_id(client, token)
    targets = client.get(f'/api/v1/organizations/{org_id}/sustainability-targets', headers=auth_headers(token))
    assert targets.status_code == 200, targets.text
    items = targets.json()['items']
    assert items
    target_id = items[0]['id']
    progress = client.get(f'/api/v1/organizations/{org_id}/sustainability-targets/{target_id}/progress', headers=auth_headers(token))
    assert progress.status_code == 200, progress.text
    assert 'progress' in progress.json()

def test_executive_report_csv(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    response = client.get(f'/api/v1/organizations/{org_id}/reports/executive', params={'format': 'csv'}, headers=auth_headers(token))
    assert response.status_code == 200, response.text
    assert 'text/csv' in response.headers.get('content-type', '')
    assert 'reportType' in response.text
