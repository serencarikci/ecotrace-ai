from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from ecotrace.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    installation_service,
    period_binding_service,
    product_profile_service,
)
from ecotrace.modules.cbam.application.concurrency import check_row_version
from ecotrace.modules.cbam.application.installation_service import (
    InstallationCreate,
    InstallationUpdate,
    InstallationVersionRequest,
)
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileVersionRequest,
    reject_classification_ready_true,
)
from ecotrace.modules.cbam.infrastructure.models import CbamReportingPeriodBinding
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import AuditLog, User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.products.infrastructure.models import Product
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


def _demo_org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _org_admin(db):
    return db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()


def _viewer(db):
    return db.execute(
        select(User).where(User.normalized_email == "viewer@ecotrace.dev")
    ).scalar_one()


def _facility(db, org_id: uuid.UUID) -> Facility:
    return db.execute(
        select(Facility).where(Facility.organization_id == org_id).limit(1)
    ).scalar_one()


def _product(db, org_id: uuid.UUID) -> Product:
    return db.execute(
        select(Product).where(Product.organization_id == org_id).limit(1)
    ).scalar_one()


def test_check_row_version_conflict() -> None:
    with pytest.raises(ConflictError):
        check_row_version(2, 1, entity="CBAM installation profile")


def test_installation_lifecycle_and_pilot_cardinality(seeded_db) -> None:
    org = _demo_org(seeded_db)
    admin = _org_admin(seeded_db)
    facility = _facility(seeded_db, org.id)
    created = installation_service.create_installation(
        seeded_db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"INST-{uuid.uuid4().hex[:8]}",
            name="Pilot Installation",
        ),
    )
    assert created.status == "draft"
    assert created.row_version == 1

    activated = installation_service.activate_installation(
        seeded_db,
        admin,
        org.id,
        created.id,
        InstallationVersionRequest(row_version=created.row_version),
    )
    assert activated.status == "active"
    assert activated.row_version == 2

    duplicate = installation_service.create_installation(
        seeded_db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"INST-{uuid.uuid4().hex[:8]}",
            name="Second Draft Same Facility",
        ),
    )
    with pytest.raises(ConflictError) as exc:
        installation_service.activate_installation(
            seeded_db,
            admin,
            org.id,
            duplicate.id,
            InstallationVersionRequest(row_version=duplicate.row_version),
        )
    assert "Pilot constraint" in str(exc.value)

    archived = installation_service.archive_installation(
        seeded_db,
        admin,
        org.id,
        activated.id,
        InstallationVersionRequest(row_version=activated.row_version),
    )
    assert archived.status == "archived"

    audit = seeded_db.execute(
        select(AuditLog).where(
            AuditLog.action == "cbam.installation.activated",
            AuditLog.entity_id == str(created.id),
        )
    ).scalar_one()
    assert audit.organization_id == org.id


def test_installation_stale_version_conflict(seeded_db) -> None:
    org = _demo_org(seeded_db)
    admin = _org_admin(seeded_db)
    facility = _facility(seeded_db, org.id)
    created = installation_service.create_installation(
        seeded_db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"INST-{uuid.uuid4().hex[:8]}",
            name="Versioned",
        ),
    )
    with pytest.raises(ConflictError):
        installation_service.update_installation(
            seeded_db,
            admin,
            org.id,
            created.id,
            InstallationUpdate(row_version=99, name="Nope"),
        )


def test_installation_wrong_org_facility_not_found(seeded_db) -> None:
    org = _demo_org(seeded_db)
    admin = _org_admin(seeded_db)
    other = Organization(
        id=uuid.uuid4(),
        name="Other Org",
        slug=f"other-{uuid.uuid4().hex[:8]}",
        country_code="DE",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(other)
    seeded_db.flush()
    foreign_facility = Facility(
        organization_id=other.id,
        code="FOREIGN",
        name="Foreign Facility",
        facility_type="office",
        country_code="DE",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(foreign_facility)
    seeded_db.commit()
    with pytest.raises(NotFoundError):
        installation_service.create_installation(
            seeded_db,
            admin,
            org.id,
            InstallationCreate(
                facility_id=foreign_facility.id,
                code=f"INST-{uuid.uuid4().hex[:8]}",
                name="Cross",
            ),
        )


def test_period_binding_open_requires_usable_installation(seeded_db) -> None:
    org = _demo_org(seeded_db)
    admin = _org_admin(seeded_db)
    empty_org = Organization(
        id=uuid.uuid4(),
        name="Empty CBAM Org",
        slug=f"empty-cbam-{uuid.uuid4().hex[:8]}",
        country_code="TR",
        timezone="UTC",
        is_active=True,
    )
    seeded_db.add(empty_org)
    seeded_db.flush()
    empty_period = ReportingPeriod(
        organization_id=empty_org.id,
        code="2024-Q1",
        name="Q1",
        period_type="quarter",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        status="open",
    )
    seeded_db.add(empty_period)
    seeded_db.commit()

    sys_admin = seeded_db.execute(
        select(User).where(User.normalized_email == "admin@ecotrace.dev")
    ).scalar_one()
    binding = period_binding_service.create_period_binding(
        seeded_db,
        sys_admin,
        empty_org.id,
        PeriodBindingCreate(reporting_period_id=empty_period.id),
    )
    with pytest.raises(BusinessRuleError) as exc:
        period_binding_service.open_data_collection(
            seeded_db,
            sys_admin,
            empty_org.id,
            binding.id,
            PeriodBindingVersionRequest(row_version=binding.row_version),
        )
    assert "usable CBAM installation" in str(exc.value)

    facility = _facility(seeded_db, org.id)
    installation_service.create_installation(
        seeded_db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"INST-{uuid.uuid4().hex[:8]}",
            name="For Period",
        ),
    )
    demo_period = ReportingPeriod(
        organization_id=org.id,
        code=f"CBAM-{uuid.uuid4().hex[:6]}",
        name="CBAM Test Period",
        period_type="quarter",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        status="open",
    )
    seeded_db.add(demo_period)
    seeded_db.commit()
    demo_binding = period_binding_service.create_period_binding(
        seeded_db,
        admin,
        org.id,
        PeriodBindingCreate(reporting_period_id=demo_period.id),
    )
    opened = period_binding_service.open_data_collection(
        seeded_db,
        admin,
        org.id,
        demo_binding.id,
        PeriodBindingVersionRequest(row_version=demo_binding.row_version),
    )
    assert opened.status == "data_collection"

    with pytest.raises(BusinessRuleError):
        period_binding_service.open_data_collection(
            seeded_db,
            admin,
            org.id,
            opened.id,
            PeriodBindingVersionRequest(row_version=opened.row_version),
        )


def test_period_binding_locked_status_blocks_mutation(seeded_db) -> None:
    org = _demo_org(seeded_db)
    admin = _org_admin(seeded_db)
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"LOCK-{uuid.uuid4().hex[:6]}",
        name="Lock Test",
        period_type="quarter",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        status="open",
    )
    seeded_db.add(period)
    seeded_db.flush()
    binding = CbamReportingPeriodBinding(
        organization_id=org.id,
        reporting_period_id=period.id,
        status="locked",
        revision_number=0,
        row_version=1,
        created_by_user_id=admin.id,
        updated_by_user_id=admin.id,
    )
    seeded_db.add(binding)
    seeded_db.commit()
    with pytest.raises(BusinessRuleError) as exc:
        period_binding_service.archive_period_binding(
            seeded_db,
            admin,
            org.id,
            binding.id,
            PeriodBindingVersionRequest(row_version=1),
        )
    assert "D-030" in str(exc.value.details)


def test_product_profile_draft_only_and_classification_fail_closed(seeded_db) -> None:
    org = _demo_org(seeded_db)
    admin = _org_admin(seeded_db)
    product = _product(seeded_db, org.id)
    created = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(product_id=product.id),
    )
    assert created.status == "draft"
    assert created.classification_ready is False
    assert any(i.code == "CN_CODE_REQUIRED" for i in created.missing_requirements)

    with pytest.raises(BusinessRuleError):
        reject_classification_ready_true()

    archived = product_profile_service.archive_product_profile(
        seeded_db,
        admin,
        org.id,
        created.id,
        ProductProfileVersionRequest(row_version=created.row_version),
    )
    assert archived.status == "archived"
    assert archived.classification_ready is False


def test_viewer_cannot_configure_installation(seeded_db) -> None:
    from ecotrace.core.exceptions import AuthorizationError

    org = _demo_org(seeded_db)
    viewer = _viewer(seeded_db)
    facility = _facility(seeded_db, org.id)
    with pytest.raises(AuthorizationError):
        installation_service.create_installation(
            seeded_db,
            viewer,
            org.id,
            InstallationCreate(
                facility_id=facility.id,
                code=f"INST-{uuid.uuid4().hex[:8]}",
                name="Denied",
            ),
        )
