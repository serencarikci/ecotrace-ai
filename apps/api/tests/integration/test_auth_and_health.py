from __future__ import annotations
from fastapi.testclient import TestClient

def test_health(client: TestClient) -> None:
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
    assert 'X-Request-ID' in response.headers

def test_ready(client: TestClient) -> None:
    response = client.get('/ready')
    assert response.status_code == 200
    assert response.json()['database'] == 'ok'

def test_meta(client: TestClient) -> None:
    response = client.get('/api/v1/meta')
    assert response.status_code == 200
    body = response.json()
    assert body['name'] == 'EcoTrace AI'
    assert body['apiVersion'] == 'v1'
    assert body['version'] == '0.7.1'
    assert 'environment' in body

def test_login_success(client: TestClient) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'admin@ecotrace.dev', 'password': 'EcoTraceAdmin!2024'})
    assert response.status_code == 200
    body = response.json()
    assert 'accessToken' in body
    assert 'refreshToken' in body
    assert body['tokenType'] == 'bearer'
    assert body['user']['email'] == 'admin@ecotrace.dev'
    assert 'system_admin' in body['user']['roles']

def test_login_failure(client: TestClient) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'admin@ecotrace.dev', 'password': 'wrong-password'})
    assert response.status_code == 401
    body = response.json()
    assert body['error']['code'] == 'INVALID_CREDENTIALS'
    assert 'requestId' in body['error']

def test_me_endpoint(client: TestClient) -> None:
    login = client.post('/api/v1/auth/login', json={'email': 'admin@ecotrace.dev', 'password': 'EcoTraceAdmin!2024'}).json()
    response = client.get('/api/v1/auth/me', headers={'Authorization': f"Bearer {login['accessToken']}"})
    assert response.status_code == 200
    assert response.json()['email'] == 'admin@ecotrace.dev'

def test_refresh_rotation(client: TestClient) -> None:
    login = client.post('/api/v1/auth/login', json={'email': 'admin@ecotrace.dev', 'password': 'EcoTraceAdmin!2024'}).json()
    old_refresh = login['refreshToken']
    refreshed = client.post('/api/v1/auth/refresh', json={'refreshToken': old_refresh})
    assert refreshed.status_code == 200
    new_body = refreshed.json()
    assert new_body['refreshToken'] != old_refresh
    reuse = client.post('/api/v1/auth/refresh', json={'refreshToken': old_refresh})
    assert reuse.status_code == 401
    assert reuse.json()['error']['code'] == 'TOKEN_REUSE_DETECTED'

def test_logout(client: TestClient) -> None:
    login = client.post('/api/v1/auth/login', json={'email': 'admin@ecotrace.dev', 'password': 'EcoTraceAdmin!2024'}).json()
    response = client.post('/api/v1/auth/logout', json={'refreshToken': login['refreshToken']})
    assert response.status_code == 204
    refresh = client.post('/api/v1/auth/refresh', json={'refreshToken': login['refreshToken']})
    assert refresh.status_code == 401

def test_validation_error_format(client: TestClient) -> None:
    response = client.post('/api/v1/auth/login', json={'email': 'not-an-email', 'password': 'x'})
    assert response.status_code == 422
    body = response.json()
    assert body['error']['code'] == 'VALIDATION_ERROR'
    assert isinstance(body['error']['details'], list)

def test_request_id_header(client: TestClient) -> None:
    response = client.get('/health', headers={'X-Request-ID': 'test-req-12345678'})
    assert response.headers['X-Request-ID'] == 'test-req-12345678'
