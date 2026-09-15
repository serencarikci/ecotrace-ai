from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ecotrace.modules.cbam.application.ports import ProductRef
from ecotrace.modules.products.application.product_service import get_product


def require_product_in_organization(
    db: Session,
    organization_id: uuid.UUID,
    product_id: uuid.UUID,
) -> ProductRef:
    product = get_product(db, organization_id, product_id)
    return ProductRef(
        id=product.id,
        organization_id=product.organization_id,
        code=product.code,
        name=product.name,
        is_active=product.is_active,
    )
