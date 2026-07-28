from __future__ import annotations
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from ecotrace.core.exceptions import ValidationAppError
from ecotrace.core.lca_constants import BATCH_TRANSITIONS
from ecotrace.modules.products.application.validators import require_percentage
from tests.helpers import api_login, auth_headers, current_org_id

def test_percentage_bounds() -> None:
    require_percentage(Decimal('50'), 'x')
    with pytest.raises(ValidationAppError):
        require_percentage(Decimal('101'), 'x')

def test_batch_transition_map() -> None:
    assert 'in_production' in BATCH_TRANSITIONS['planned']
    assert 'released' not in BATCH_TRANSITIONS['planned']

def test_product_crud_and_archive(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    headers = auth_headers(token)
    create = client.post(f'/api/v1/organizations/{org_id}/products', headers=headers, json={'code': 'TST-PROD-1', 'name': 'Test Product', 'productType': 'finished_good', 'defaultUnitCode': 'unit', 'recyclabilityPercentage': '80', 'recycledContentPercentage': '20', 'repairabilityScore': 5, 'weightValue': '1.5'})
    assert create.status_code == 201, create.text
    product_id = create.json()['id']
    detail = client.get(f'/api/v1/organizations/{org_id}/products/{product_id}', headers=headers)
    assert detail.status_code == 200
    bad = client.post(f'/api/v1/organizations/{org_id}/products', headers=headers, json={'code': 'TST-PROD-BAD', 'name': 'Bad', 'productType': 'finished_good', 'defaultUnitCode': 'unit', 'recyclabilityPercentage': '120'})
    assert bad.status_code == 422
    archive = client.post(f'/api/v1/organizations/{org_id}/products/{product_id}/archive', headers=headers)
    assert archive.status_code == 200
    assert archive.json()['isActive'] is False

def test_supplier_material_bom_flow(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    headers = auth_headers(token)
    supplier = client.post(f'/api/v1/organizations/{org_id}/suppliers', headers=headers, json={'code': 'SUP-T1', 'name': 'Test Supplier', 'supplierType': 'raw_material', 'status': 'active', 'contactEmail': 'a@example.com', 'website': 'https://example.com', 'sustainabilityRating': 3})
    assert supplier.status_code == 201, supplier.text
    supplier_id = supplier.json()['id']
    material = client.post(f'/api/v1/organizations/{org_id}/materials', headers=headers, json={'code': 'MAT-T1', 'name': 'Test Material', 'materialCategory': 'plastic', 'defaultUnitCode': 'kg', 'supplierId': supplier_id, 'recycledContentPercentage': '50'})
    assert material.status_code == 201, material.text
    material_id = material.json()['id']
    product = client.post(f'/api/v1/organizations/{org_id}/products', headers=headers, json={'code': 'BOM-PROD', 'name': 'BOM Product', 'productType': 'finished_good', 'defaultUnitCode': 'unit'})
    assert product.status_code == 201, product.text
    product_id = product.json()['id']
    bom = client.post(f'/api/v1/organizations/{org_id}/products/{product_id}/boms', headers=headers, json={'name': 'BOM draft', 'items': [{'materialId': material_id, 'quantity': '1.25', 'unitCode': 'kg', 'wastePercentage': '5'}]})
    assert bom.status_code == 201, bom.text
    bom_id = bom.json()['id']
    submit = client.post(f'/api/v1/organizations/{org_id}/boms/{bom_id}/submit-review', headers=headers)
    assert submit.status_code == 200
    approve = client.post(f'/api/v1/organizations/{org_id}/boms/{bom_id}/approve', headers=headers)
    assert approve.status_code == 200
    assert approve.json()['status'] == 'approved'
    patch = client.patch(f'/api/v1/organizations/{org_id}/boms/{bom_id}', headers=headers, json={'name': 'changed'})
    assert patch.status_code in {400, 409, 422}
    cloned = client.post(f'/api/v1/organizations/{org_id}/boms/{bom_id}/clone-version', headers=headers)
    assert cloned.status_code == 201
    assert cloned.json()['version'] == bom.json()['version'] + 1

def test_bom_cycle_detection(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    headers = auth_headers(token)
    a = client.post(f'/api/v1/organizations/{org_id}/products', headers=headers, json={'code': 'CYC-A', 'name': 'A', 'productType': 'component', 'defaultUnitCode': 'unit'}).json()['id']
    b = client.post(f'/api/v1/organizations/{org_id}/products', headers=headers, json={'code': 'CYC-B', 'name': 'B', 'productType': 'component', 'defaultUnitCode': 'unit'}).json()['id']
    bom_a = client.post(f'/api/v1/organizations/{org_id}/products/{a}/boms', headers=headers, json={'name': 'A bom', 'items': [{'componentProductId': b, 'quantity': '1', 'unitCode': 'unit'}]})
    assert bom_a.status_code == 201, bom_a.text
    bom_b = client.post(f'/api/v1/organizations/{org_id}/products/{b}/boms', headers=headers, json={'name': 'B bom cycle', 'items': [{'componentProductId': a, 'quantity': '1', 'unitCode': 'unit'}]})
    assert bom_b.status_code in {400, 409, 422}, bom_b.text

def test_lca_calculate_and_public_passport(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    headers = auth_headers(token)
    products = client.get(f'/api/v1/organizations/{org_id}/products', headers=headers, params={'search': 'EcoBottle'})
    assert products.status_code == 200
    items = products.json()['items']
    assert items, 'seeded EcoBottle expected'
    product_id = items[0]['id']
    studies = client.get(f'/api/v1/organizations/{org_id}/lca-studies', headers=headers, params={'search': 'LCA-PCF'})
    assert studies.status_code == 200
    study_items = studies.json()['items']
    assert study_items
    study_id = study_items[0]['id']
    results = client.get(f'/api/v1/organizations/{org_id}/lca-studies/{study_id}/results', headers=headers)
    assert results.status_code == 200, results.text
    assert 'disclaimer' in results.json()
    footprints = client.get(f'/api/v1/organizations/{org_id}/product-carbon-footprints', headers=headers, params={'productId': product_id})
    assert footprints.status_code == 200
    public = client.get('/api/v1/public/passports/ecobottle-750')
    assert public.status_code == 200, public.text
    body = public.json()
    assert body['status'] in {'published', 'revoked', 'superseded'}
    assert 'disclaimer' in body
    assert 'contactEmail' not in str(body)
    qr = client.get('/api/v1/public/passports/ecobottle-750/qr')
    assert qr.status_code == 200
    assert 'svg' in qr.json()

def test_cross_org_product_denied(client: TestClient) -> None:
    token = api_login(client, 'viewer@ecotrace.dev', 'EcoTraceViewer!2024')
    fake_org = '00000000-0000-0000-0000-000000000099'
    response = client.get(f'/api/v1/organizations/{fake_org}/products', headers=auth_headers(token))
    assert response.status_code in {403, 404}

def test_passport_publish_requires_admin_sections(client: TestClient) -> None:
    token = api_login(client, 'orgadmin@ecotrace.dev', 'EcoTraceOrgAdmin!2024')
    org_id = current_org_id(client, token)
    headers = auth_headers(token)
    products = client.get(f'/api/v1/organizations/{org_id}/products', headers=headers, params={'search': 'BioPack'}).json()['items']
    product_id = products[0]['id']
    create = client.post(f'/api/v1/organizations/{org_id}/digital-product-passports', headers=headers, json={'productId': product_id, 'passportCode': 'DPP-TEST-PUB', 'title': 'Test passport', 'publicSlug': 'test-passport-publish', 'sections': [{'sectionCode': 'product_identity', 'title': 'Identity', 'displayOrder': 1, 'isPublic': True, 'structuredDataJson': {'name': 'x'}}, {'sectionCode': 'manufacturer', 'title': 'Manufacturer', 'displayOrder': 2, 'isPublic': True, 'structuredDataJson': {'name': 'y'}}]})
    assert create.status_code == 201, create.text
    passport_id = create.json()['id']
    publish = client.post(f'/api/v1/organizations/{org_id}/digital-product-passports/{passport_id}/publish', headers=headers)
    assert publish.status_code == 200, publish.text
    assert publish.json()['status'] == 'published'
    revoke = client.post(f'/api/v1/organizations/{org_id}/digital-product-passports/{passport_id}/revoke', headers=headers)
    assert revoke.status_code == 200
    public = client.get('/api/v1/public/passports/test-passport-publish')
    assert public.status_code == 200
    assert public.json()['status'] == 'revoked'
