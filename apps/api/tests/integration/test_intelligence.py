from __future__ import annotations
from fastapi.testclient import TestClient
from tests.helpers import api_login, auth_headers, current_org_id

def test_agents_catalog_and_execute(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    catalog = client.get('/api/v1/agents', headers=auth_headers(token))
    assert catalog.status_code == 200, catalog.text
    codes = {a['code'] for a in catalog.json()}
    assert 'carbon_analysis' in codes
    run = client.post(f'/api/v1/organizations/{org_id}/agents/carbon_analysis/execute', headers=auth_headers(token), json={'prompt': 'Summarize our carbon inventory status for this organization.'})
    assert run.status_code == 200, run.text
    body = run.json()
    assert body['status'] in {'completed', 'completed_with_warnings', 'awaiting_approval'}
    assert 'resultSummary' in body or 'id' in body

def test_agent_cross_org_rejected(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    foreign = '00000000-0000-4000-8000-000000000099'
    response = client.post(f'/api/v1/organizations/{foreign}/agents/carbon_analysis/execute', headers=auth_headers(token), json={'prompt': 'leak'})
    assert response.status_code in {403, 404}

def test_automation_crud_activate_run(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    created = client.post(f'/api/v1/organizations/{org_id}/automation-rules', headers=auth_headers(token), json={'code': 'itest-weekly-anomaly', 'name': 'IT weekly anomaly', 'templateCode': 'weekly_anomaly_scan'})
    assert created.status_code == 200, created.text
    rule_id = created.json()['id']
    activated = client.post(f'/api/v1/organizations/{org_id}/automation-rules/{rule_id}/activate', headers=auth_headers(token))
    assert activated.status_code == 200, activated.text
    assert activated.json()['status'] == 'active'
    run1 = client.post(f'/api/v1/organizations/{org_id}/automation-rules/{rule_id}/run', headers=auth_headers(token))
    assert run1.status_code == 200, run1.text
    paused = client.post(f'/api/v1/organizations/{org_id}/automation-rules/{rule_id}/pause', headers=auth_headers(token))
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

def test_anomaly_and_data_quality_scan(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    rules = client.get(f'/api/v1/organizations/{org_id}/anomaly-rules', headers=auth_headers(token))
    assert rules.status_code == 200
    assert len(rules.json()) >= 1
    rule_id = rules.json()[0]['id']
    ran = client.post(f'/api/v1/organizations/{org_id}/anomaly-rules/{rule_id}/run', headers=auth_headers(token))
    assert ran.status_code == 200, ran.text
    dq = client.post(f'/api/v1/organizations/{org_id}/data-quality/scan', headers=auth_headers(token))
    assert dq.status_code == 200, dq.text
    alerts = client.get(f'/api/v1/organizations/{org_id}/alerts', headers=auth_headers(token))
    assert alerts.status_code == 200

def test_forecast_definition_list(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    defs = client.get(f'/api/v1/organizations/{org_id}/forecast-definitions', headers=auth_headers(token))
    assert defs.status_code == 200
    assert any((d['code'] == 'total-emissions-fc' for d in defs.json()))

def test_notifications_and_regulatory_disclaimer_seed(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    unread = client.get('/api/v1/notifications/unread-count', headers=auth_headers(token))
    assert unread.status_code == 200
    docs = client.get('/api/v1/regulatory-documents', headers=auth_headers(token))
    assert docs.status_code == 200
    assert any(('DEMO' in d.get('regulationCode', '') for d in docs.json()))

def test_system_health_requires_admin(client: TestClient) -> None:
    viewer = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    denied = client.get('/api/v1/system/health', headers=auth_headers(viewer))
    assert denied.status_code in {403, 401}
    admin = api_login(client, 'admin@ecotrace.dev', 'EcoTraceAdmin!2024')
    ok = client.get('/api/v1/system/health', headers=auth_headers(admin))
    assert ok.status_code == 200, ok.text
    assert ok.json()['status'] in {'ok', 'degraded'}

def test_scheduled_report_run(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    created = client.post(f'/api/v1/organizations/{org_id}/scheduled-reports', headers=auth_headers(token), json={'code': 'itest-exec-report', 'name': 'IT Executive Report', 'reportType': 'executive_sustainability_summary', 'scheduleExpression': 'monthly', 'outputFormat': 'json'})
    assert created.status_code == 200, created.text
    report_id = created.json()['id']
    client.post(f'/api/v1/organizations/{org_id}/scheduled-reports/{report_id}/activate', headers=auth_headers(token))
    ran = client.post(f'/api/v1/organizations/{org_id}/scheduled-reports/{report_id}/run', headers=auth_headers(token))
    assert ran.status_code == 200, ran.text
    generated = client.get(f'/api/v1/organizations/{org_id}/generated-reports', headers=auth_headers(token))
    assert generated.status_code == 200
    assert len(generated.json()) >= 1
