"""Shared helpers for CBAM production ↔ product-profile tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application import product_profile_service
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileVersionRequest,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.products.infrastructure.models import Product


def ensure_org_product(
    db: Session,
    organization_id: uuid.UUID,
    *,
    code: str | None = None,
) -> Product:
    code = code or f'PR-{uuid.uuid4().hex[:8]}'
    existing = db.execute(
        select(Product).where(
            Product.organization_id == organization_id,
            Product.code == code,
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    row = Product(
        organization_id=organization_id,
        code=code,
        name=f'Test product {code}',
        product_type='finished_good',
        default_unit_code='t',
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def create_active_ready_profile(
    db: Session,
    user: User,
    organization_id: uuid.UUID,
    *,
    product: Product | None = None,
    cn_code: str = '73181595',
) -> product_profile_service.ProductProfileResponse:
    product = product or ensure_org_product(db, organization_id)
    draft = product_profile_service.create_product_profile(
        db,
        user,
        organization_id,
        ProductProfileCreate(
            product_id=product.id,
            product_name=product.name,
            cn_code=cn_code,
            reducing_agent='Natural gas',
            steel_mill_identification_number='TR-TEST-001',
            percent_mn=Decimal('40'),
            percent_cr=Decimal('20'),
            percent_ni=Decimal('10'),
            percent_other_alloys=Decimal('10'),
            percent_other_materials=Decimal('20'),
        ),
    )
    return product_profile_service.publish_product_profile(
        db,
        user,
        organization_id,
        draft.id,
        ProductProfileVersionRequest(row_version=draft.row_version),
    )
