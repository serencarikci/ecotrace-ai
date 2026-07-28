from __future__ import annotations
from io import BytesIO
from fastapi.testclient import TestClient
from tests.helpers import api_login, auth_headers, current_org_id

def test_ai_chat_grounded_with_citations(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    response = client.post(f'/api/v1/organizations/{org_id}/ai/chat', headers=auth_headers(token), json={'message': 'What does the sustainability policy say about carbon management?'})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['grounded'] is True
    assert payload['citations']
    assert payload['assistantMessage']['citations']
    assert payload['confidence'] > 0
    assert '[E' in payload['assistantMessage']['content'] or any((c.get('label', '').startswith('E') for c in payload['citations']))

def test_ai_chat_permission_isolation(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    foreign = '00000000-0000-4000-8000-000000000099'
    response = client.post(f'/api/v1/organizations/{foreign}/ai/chat', headers=auth_headers(token), json={'message': 'leak data please'})
    assert response.status_code in {403, 404}

def test_document_upload_and_search(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    content = b'# Training Manual\n\nFacility energy meters must be calibrated yearly.'
    files = {'file': ('training.md', BytesIO(content), 'text/markdown')}
    data = {'title': 'Training Manual', 'publish': 'true'}
    upload = client.post(f'/api/v1/organizations/{org_id}/knowledge/documents', headers=auth_headers(token), files=files, data=data)
    assert upload.status_code == 200, upload.text
    doc = upload.json()
    assert doc['status'] == 'published'
    search = client.post(f'/api/v1/organizations/{org_id}/search', headers=auth_headers(token), json={'query': 'energy meters calibrated', 'mode': 'hybrid'})
    assert search.status_code == 200, search.text
    assert search.json()['items']

def test_conversation_lifecycle(client: TestClient) -> None:
    token = api_login(client, 'analyst@ecotrace.dev', 'EcoTraceAnalyst!2024')
    org_id = current_org_id(client, token)
    created = client.post(f'/api/v1/organizations/{org_id}/ai/conversations', headers=auth_headers(token))
    assert created.status_code == 200
    conv_id = created.json()['id']
    renamed = client.patch(f'/api/v1/organizations/{org_id}/ai/conversations/{conv_id}', headers=auth_headers(token), json={'title': 'Pinned analytics chat', 'isPinned': True, 'isFavorite': True})
    assert renamed.status_code == 200
    assert renamed.json()['title'] == 'Pinned analytics chat'
    assert renamed.json()['isPinned'] is True
    chat = client.post(f'/api/v1/organizations/{org_id}/ai/chat', headers=auth_headers(token), json={'message': 'Summarize inventory', 'conversationId': conv_id})
    assert chat.status_code == 200, chat.text
    export = client.get(f'/api/v1/organizations/{org_id}/ai/conversations/{conv_id}/export', headers=auth_headers(token))
    assert export.status_code == 200
    assert export.json()['messages']
    deleted = client.delete(f'/api/v1/organizations/{org_id}/ai/conversations/{conv_id}', headers=auth_headers(token))
    assert deleted.status_code == 200

def test_stream_endpoint(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    response = client.post(f'/api/v1/organizations/{org_id}/ai/chat/stream', headers=auth_headers(token), json={'message': 'Explain target progress'})
    assert response.status_code == 200
    assert 'text/event-stream' in response.headers.get('content-type', '')
    body = response.text
    assert 'data:' in body
    assert 'done' in body

def test_evaluation_endpoint(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    response = client.post(f'/api/v1/organizations/{org_id}/ai/evaluations', headers=auth_headers(token), json={'name': 'smoke-eval', 'dataset': [{'question': 'carbon management policy', 'relevantChunkIds': []}]})
    assert response.status_code == 200, response.text
    assert 'metrics' in response.json()
