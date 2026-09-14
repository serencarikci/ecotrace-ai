"""HTTP helpers for CBAM product-profile setup in API tests."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def create_published_steel_profile(
    client: TestClient,
    token: str,
    org_id: str,
    *,
    headers: dict[str, str],
) -> str:
    """Return active ready product-profile version id via HTTP API."""
    product = client.post(
        f'/api/v1/organizations/{org_id}/products',
        headers=headers,
        json={
            'code': f'CBAM-{uuid.uuid4().hex[:8]}',
            'name': 'CBAM test product',
            'productType': 'finished_good',
            'defaultUnitCode': 't',
        },
    )
    assert product.status_code in (200, 201), product.text
    product_id = product.json()['id']
    draft = client.post(
        f'/api/v1/cbam/organizations/{org_id}/product-profile-versions',
        headers=headers,
        json={
            'productId': product_id,
            'productName': 'CBAM screws',
            'cnCode': '73181595',
            'reducingAgent': 'Natural gas',
            'steelMillIdentificationNumber': 'TR-API-1',
            'percentMn': '40',
            'percentCr': '20',
            'percentNi': '10',
            'percentOtherAlloys': '10',
            'percentOtherMaterials': '20',
        },
    )
    assert draft.status_code == 201, draft.text
    published = client.post(
        f"/api/v1/cbam/organizations/{org_id}/product-profile-versions/{draft.json()['id']}/publish",
        headers=headers,
        json={'rowVersion': draft.json()['rowVersion']},
    )
    assert published.status_code == 200, published.text
    assert published.json()['status'] == 'active'
    assert published.json()['classificationReady'] is True
    return published.json()['id']
