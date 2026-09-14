"""Regression: seed_lca must resolve PCF by explicit study identity (idempotent)."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import MultipleResultsFound

from ecotrace.db.seed import DEMO_ORG_SLUG, run_seed
from ecotrace.db.seed_lca import seed_lca
from ecotrace.modules.digital_product_passport.infrastructure.models import (
    DigitalProductPassport,
)
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.lifecycle_assessment.infrastructure.models import LcaStudy
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.product_carbon_footprint.infrastructure.models import (
    ProductCarbonFootprint,
)
from ecotrace.modules.products.infrastructure.models import Product


def test_seed_lca_pcf_resolution_is_study_scoped_and_idempotent(seeded_db) -> None:
    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    actor = seeded_db.execute(
        select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
    ).scalar_one()
    bottle = seeded_db.execute(
        select(Product).where(Product.organization_id == org.id, Product.code == 'EB750')
    ).scalar_one()

    studies = list(
        seeded_db.execute(
            select(LcaStudy).where(
                LcaStudy.organization_id == org.id,
                LcaStudy.code.in_(('LCA-CTG-EB750', 'LCA-CGR-EB750', 'LCA-PCF-EB750')),
            )
        ).scalars()
    )
    assert len(studies) == 3
    pcfs = []
    for study in studies:
        for pcf in seeded_db.execute(
            select(ProductCarbonFootprint).where(
                ProductCarbonFootprint.lca_study_id == study.id
            )
        ).scalars():
            pcf.status = 'approved'
            pcf.product_id = bottle.id
            pcf.organization_id = org.id
            pcfs.append(pcf)
    seeded_db.flush()
    if len(pcfs) < 2:
        pytest.skip('LCA seed did not materialize enough PCF rows in this environment')

    # Ambiguous lookup (the pre-fix bug) must raise with multiple approved rows.
    with pytest.raises(MultipleResultsFound):
        seeded_db.execute(
            select(ProductCarbonFootprint).where(
                ProductCarbonFootprint.organization_id == org.id,
                ProductCarbonFootprint.product_id == bottle.id,
                ProductCarbonFootprint.status == 'approved',
            )
        ).scalar_one_or_none()

    pcf_study = next(s for s in studies if s.code == 'LCA-PCF-EB750')
    scoped = seeded_db.execute(
        select(ProductCarbonFootprint).where(
            ProductCarbonFootprint.organization_id == org.id,
            ProductCarbonFootprint.product_id == bottle.id,
            ProductCarbonFootprint.lca_study_id == pcf_study.id,
            ProductCarbonFootprint.status == 'approved',
        )
    ).scalar_one_or_none()
    assert scoped is not None

    # Fixed seed path must remain idempotent (no MultipleResultsFound).
    seed_lca(seeded_db, org, actor)
    seed_lca(seeded_db, org, actor)
    seeded_db.flush()
    assert (
        seeded_db.execute(
            select(DigitalProductPassport).where(
                DigitalProductPassport.organization_id == org.id,
                DigitalProductPassport.passport_code == 'DPP-EB750-V1',
            )
        ).scalar_one_or_none()
        is not None
    )


def test_run_seed_twice_does_not_raise_on_lca(seeded_db) -> None:
    run_seed(seeded_db)
    run_seed(seeded_db)
    org = seeded_db.execute(
        select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
    ).scalar_one()
    assert (
        seeded_db.execute(
            select(DigitalProductPassport).where(
                DigitalProductPassport.organization_id == org.id,
                DigitalProductPassport.passport_code == 'DPP-EB750-V1',
            )
        ).scalar_one_or_none()
        is not None
    )
