"""Phase 6C production ↔ product-profile linkage tests."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from tests.cbam_profile_helpers import create_active_ready_profile, ensure_org_product

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    installation_service,
    period_binding_service,
    product_profile_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileVersionRequest,
)
from ecotrace.modules.cbam.application.production_record_service import (
    ProductionRecordCreate,
    ProductionRecordUpdate,
)
from ecotrace.modules.cbam.infrastructure.models import CbamProductionRecord
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


def _org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db):
    return db.execute(
        select(User).where(User.normalized_email == 'orgadmin@ecotrace.dev')
    ).scalar_one()


def _setup(db, admin, org):
    facility = db.execute(
        select(Facility).where(Facility.organization_id == org.id).limit(1)
    ).scalar_one()
    installation_service.create_installation(
        db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f'P6C-{uuid.uuid4().hex[:8]}',
            name='P6C Installation',
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f'P6C-{uuid.uuid4().hex[:6]}',
        name='P6C Period',
        period_type='custom',
        start_date=__import__('datetime').date(2030, 1, 1),
        end_date=__import__('datetime').date(2030, 3, 31),
        status='open',
    )
    db.add(period)
    db.flush()
    binding = period_binding_service.create_period_binding(
        db, admin, org.id, PeriodBindingCreate(reporting_period_id=period.id)
    )
    opened = period_binding_service.open_data_collection(
        db,
        admin,
        org.id,
        binding.id,
        PeriodBindingVersionRequest(row_version=binding.row_version),
    )
    installation = installation_service.list_installations(
        db, admin, org.id, page=1, page_size=50
    ).items[-1]
    return opened, installation


def test_same_org_active_ready_profile_can_be_linked(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    created = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            quantity=Decimal('12.5'),
            unit='t',
        ),
    )
    assert created.product_profile_version_id == profile.id
    assert created.profile_link_status == 'READY'
    assert created.profile_link_issue_codes == []
    assert created.product_id == profile.product_id
    assert created.profile_version == profile.version
    assert created.quantity == Decimal('12.5')


def test_draft_and_not_ready_profiles_rejected(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    product = ensure_org_product(seeded_db, org.id, code='DRAFT-P')
    draft = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name='Draft only',
            cn_code='73181595',
        ),
    )
    with pytest.raises(BusinessRuleError) as draft_exc:
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=draft.id,
                quantity=Decimal('1'),
                unit='t',
            ),
        )
    assert draft_exc.value.details[0]['code'] == 'PRODUCT_PROFILE_NOT_ACTIVE'

    not_ready = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(product_id=product.id, product_name='Incomplete', cn_code='73181595'),
    )
    assert not_ready.classification_ready is False
    with pytest.raises(BusinessRuleError) as nr_exc:
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=not_ready.id,
                quantity=Decimal('1'),
                unit='t',
            ),
        )
    assert nr_exc.value.details[0]['code'] == 'PRODUCT_PROFILE_NOT_ACTIVE'


def test_superseded_rejected_for_new_link_but_historical_readable(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    product = ensure_org_product(seeded_db, org.id, code='HIST-P')
    v1 = create_active_ready_profile(seeded_db, admin, org.id, product=product)
    record = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=v1.id,
            quantity=Decimal('3'),
            unit='t',
        ),
    )
    linked_id = record.product_profile_version_id
    # Publish v2 → supersedes v1; must not rewrite production.
    v2 = create_active_ready_profile(seeded_db, admin, org.id, product=product)
    assert v2.version == 2
    still = production_record_service.get_production_record(
        seeded_db, admin, org.id, record.id
    )
    assert still.product_profile_version_id == linked_id
    assert still.profile_link_status == 'OUTDATED'
    assert still.profile_status == 'superseded'

    with pytest.raises(BusinessRuleError) as exc:
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=v1.id,
                quantity=Decimal('1'),
                unit='t',
            ),
        )
    assert exc.value.details[0]['code'] == 'PRODUCT_PROFILE_NOT_ACTIVE'


def test_archived_profile_rejected_for_new_link(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    archived = product_profile_service.archive_product_profile(
        seeded_db,
        admin,
        org.id,
        profile.id,
        ProductProfileVersionRequest(row_version=profile.row_version),
    )
    assert archived.status == 'archived'
    with pytest.raises(BusinessRuleError) as exc:
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=archived.id,
                quantity=Decimal('1'),
                unit='t',
            ),
        )
    assert exc.value.details[0]['code'] == 'PRODUCT_PROFILE_ARCHIVED'


def test_missing_profile_required_on_create(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    with pytest.raises(BusinessRuleError) as exc:
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                quantity=Decimal('1'),
                unit='t',
            ),
        )
    assert exc.value.details[0]['code'] == 'PRODUCT_PROFILE_REQUIRED'


def test_legacy_null_profile_readable_and_linkable(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    # Historical row inserted without going through create validation.
    legacy = CbamProductionRecord(
        organization_id=org.id,
        reporting_period_binding_id=binding.id,
        installation_profile_id=installation.id,
        product_profile_version_id=None,
        quantity=Decimal('8'),
        unit='t',
        source_type='MANUAL',
        status='active',
        row_version=1,
    )
    seeded_db.add(legacy)
    seeded_db.flush()
    viewed = production_record_service.get_production_record(
        seeded_db, admin, org.id, legacy.id
    )
    assert viewed.profile_link_status == 'MISSING'
    assert 'PRODUCT_PROFILE_REQUIRED' in viewed.profile_link_issue_codes
    summary = production_record_service.get_production_profile_link_summary(
        seeded_db, admin, org.id, binding.id
    )
    assert summary.missing_profile_count == 1
    assert summary.allocation_profile_ready is False
    assert 'PRODUCTION_PROFILE_LINK_MISSING' in summary.blocking_issue_codes

    profile = create_active_ready_profile(seeded_db, admin, org.id)
    linked = production_record_service.update_production_record(
        seeded_db,
        admin,
        org.id,
        legacy.id,
        ProductionRecordUpdate(
            row_version=viewed.row_version,
            product_profile_version_id=profile.id,
        ),
    )
    assert linked.profile_link_status == 'READY'
    summary2 = production_record_service.get_production_profile_link_summary(
        seeded_db, admin, org.id, binding.id
    )
    assert summary2.missing_profile_count == 0
    assert summary2.eligible_record_count == 1
    assert summary2.allocation_profile_ready is True


def test_cross_org_profile_fail_closed(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    with pytest.raises((NotFoundError, BusinessRuleError)):
        production_record_service.create_production_record(
            seeded_db,
            admin,
            uuid.uuid4(),
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=profile.id,
                quantity=Decimal('1'),
                unit='t',
            ),
        )


def test_update_rejects_clearing_profile(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    created = production_record_service.create_production_record(
        seeded_db,
        admin,
        org.id,
        binding.id,
        ProductionRecordCreate(
            installation_profile_id=installation.id,
            product_profile_version_id=profile.id,
            quantity=Decimal('2'),
            unit='t',
        ),
    )
    with pytest.raises(BusinessRuleError) as exc:
        production_record_service.update_production_record(
            seeded_db,
            admin,
            org.id,
            created.id,
            ProductionRecordUpdate(
                row_version=created.row_version,
                product_profile_version_id=None,
            ),
        )
    assert exc.value.details[0]['code'] == 'PRODUCT_PROFILE_REQUIRED'


def test_unit_and_quantity_rules_unchanged(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    binding, installation = _setup(seeded_db, admin, org)
    profile = create_active_ready_profile(seeded_db, admin, org.id)
    from ecotrace.core.exceptions import ValidationAppError

    with pytest.raises(ValidationAppError):
        production_record_service.create_production_record(
            seeded_db,
            admin,
            org.id,
            binding.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=profile.id,
                quantity=Decimal('0'),
                unit='t',
            ),
        )
