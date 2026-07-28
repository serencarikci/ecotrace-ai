from __future__ import annotations
from fastapi.testclient import TestClient

def api_login(client: TestClient, email: str, password: str) -> str:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200, response.text
    return response.json()['accessToken']

def auth_headers(token: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {token}'}

def current_org_id(client: TestClient, token: str) -> str:
    response = client.get('/api/v1/auth/me/organizations', headers=auth_headers(token))
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list) and data
    return data[0]['organizationId']
