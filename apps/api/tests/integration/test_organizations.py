from __future__ import annotations
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.helpers import api_login as _login
from ecotrace.db.seed import run_seed
from ecotrace.modules.identity.infrastructure.models import Role, User
from ecotrace.modules.organizations.infrastructure.models import Organization

def test_organization_list_as_admin(client: TestClient) -> None:
    token = _login(client, 'admin@ecotrace.dev', 'EcoTraceAdmin!2024')
    response = client.get('/api/v1/organizations', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    body = response.json()
    assert body['totalItems'] >= 1
    assert body['page'] == 1
    assert 'items' in body

def test_organization_list_as_viewer(client: TestClient) -> None:
    token = _login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    response = client.get('/api/v1/organizations', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json()['totalItems'] >= 1

def test_organization_creation_authorization(client: TestClient) -> None:
    viewer_token = _login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    denied = client.post('/api/v1/organizations', headers={'Authorization': f'Bearer {viewer_token}'}, json={'name': 'Blocked Org', 'slug': 'blocked-org', 'countryCode': 'US', 'timezone': 'UTC', 'isActive': True})
    assert denied.status_code == 403
    admin_token = _login(client, 'admin@ecotrace.dev', 'EcoTraceAdmin!2024')
    created = client.post('/api/v1/organizations', headers={'Authorization': f'Bearer {admin_token}'}, json={'name': 'New Org', 'slug': 'new-org', 'legalName': 'New Org LLC', 'countryCode': 'US', 'timezone': 'UTC', 'isActive': True})
    assert created.status_code == 201
    assert created.json()['slug'] == 'new-org'

def test_organization_update_authorization(client: TestClient) -> None:
    admin_token = _login(client, 'admin@ecotrace.dev', 'EcoTraceAdmin!2024')
    listing = client.get('/api/v1/organizations', headers={'Authorization': f'Bearer {admin_token}'}).json()
    org_id = listing['items'][0]['id']
    org_admin_token = _login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    updated = client.patch(f'/api/v1/organizations/{org_id}', headers={'Authorization': f'Bearer {org_admin_token}'}, json={'name': 'EcoTrace Demo Industries Updated'})
    assert updated.status_code == 200
    assert 'Updated' in updated.json()['name']
    viewer_token = _login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    denied = client.patch(f'/api/v1/organizations/{org_id}', headers={'Authorization': f'Bearer {viewer_token}'}, json={'name': 'Should Fail'})
    assert denied.status_code == 403

def test_seed_idempotency(seeded_db: Session) -> None:
    users_before = seeded_db.execute(select(func.count()).select_from(User)).scalar_one()
    roles_before = seeded_db.execute(select(func.count()).select_from(Role)).scalar_one()
    orgs_before = seeded_db.execute(select(func.count()).select_from(Organization)).scalar_one()
    run_seed(seeded_db)
    users_after = seeded_db.execute(select(func.count()).select_from(User)).scalar_one()
    roles_after = seeded_db.execute(select(func.count()).select_from(Role)).scalar_one()
    orgs_after = seeded_db.execute(select(func.count()).select_from(Organization)).scalar_one()
    assert users_after == users_before
    assert roles_after == roles_before
    assert orgs_after == orgs_before
    assert roles_after == 5
