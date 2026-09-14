"""Phase 6A product profile lifecycle, steel validation, and readiness tests."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from ecotrace.core.exceptions import (
    AuthorizationError,
    BusinessRuleError,
    NotFoundError,
    ValidationAppError,
)
from ecotrace.db.seed import DEMO_ORG_SLUG
from ecotrace.modules.cbam.application import (
    installation_service,
    period_binding_service,
    product_profile_service,
    production_record_service,
)
from ecotrace.modules.cbam.application.cn_catalog_service import get_cn_code, resolve_cn_code
from ecotrace.modules.cbam.application.field_applicability import FIELD_APPLICABILITY_KEYS
from ecotrace.modules.cbam.application.installation_service import InstallationCreate
from ecotrace.modules.cbam.application.period_binding_service import (
    PeriodBindingCreate,
    PeriodBindingVersionRequest,
)
from ecotrace.modules.cbam.application.product_profile_service import (
    ProductProfileCreate,
    ProductProfileUpdate,
    ProductProfileVersionRequest,
    compute_classification_state,
    reject_classification_ready_true,
)
from ecotrace.modules.cbam.application.production_record_service import ProductionRecordCreate
from ecotrace.modules.cbam.infrastructure.models import CbamCnCodeDataset
from ecotrace.modules.facilities.infrastructure.models import Facility
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.products.infrastructure.models import Product
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


def _org(db):
    return db.execute(select(Organization).where(Organization.slug == DEMO_ORG_SLUG)).scalar_one()


def _admin(db):
    return db.execute(
        select(User).where(User.normalized_email == "orgadmin@ecotrace.dev")
    ).scalar_one()


def _viewer(db):
    return db.execute(
        select(User).where(User.normalized_email == "viewer@ecotrace.dev")
    ).scalar_one()


def _product(db, org_id: uuid.UUID, code: str = "STEEL-1") -> Product:
    existing = db.execute(
        select(Product).where(Product.organization_id == org_id, Product.code == code)
    ).scalar_one_or_none()
    if existing:
        return existing
    row = Product(
        organization_id=org_id,
        code=code,
        name="Steel product",
        product_type="finished_good",
        default_unit_code="t",
        is_active=True,
    )
    db.add(row)
    db.flush()
    return row


def _steel_ready_payload(product_id: uuid.UUID) -> ProductProfileCreate:
    return ProductProfileCreate(
        product_id=product_id,
        product_name="Screws lot A",
        cn_code="73181595",
        reducing_agent="Natural gas",
        steel_mill_identification_number="TR-STEEL-001",
        percent_mn=Decimal("40"),
        percent_cr=Decimal("20"),
        percent_ni=Decimal("10"),
        percent_other_alloys=Decimal("10"),
        percent_other_materials=Decimal("20"),
    )


def test_create_draft_requires_name_and_cn_for_readiness(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    created = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, ProductProfileCreate(product_id=product.id)
    )
    assert created.status == "draft"
    assert created.classification_ready is False
    codes = {i.code for i in created.missing_requirements}
    assert "PRODUCT_NAME_REQUIRED" in codes
    assert "CN_CODE_REQUIRED" in codes


def test_cn_snapshot_persisted_and_client_cannot_force_ready(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    with pytest.raises(BusinessRuleError):
        product_profile_service.create_product_profile(
            seeded_db,
            admin,
            org.id,
            ProductProfileCreate(
                product_id=product.id,
                product_name="X",
                cn_code="73181595",
                classification_ready=True,
            ),
        )
    with pytest.raises(BusinessRuleError):
        reject_classification_ready_true()
    created = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(product_id=product.id, product_name="X", cn_code="7318 15 95"),
    )
    assert created.cn_normalized_code == "73181595"
    assert created.cn_display_code == "7318 15 95"
    assert created.cn_dataset_version == "SEE_V2.1"
    assert created.cn_sector == "Iron or steel products"
    assert created.classification_ready is False


def test_steel_ready_publish_and_immutable_edit(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    draft = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, _steel_ready_payload(product.id)
    )
    assert draft.classification_ready is True
    published = product_profile_service.publish_product_profile(
        seeded_db,
        admin,
        org.id,
        draft.id,
        ProductProfileVersionRequest(row_version=draft.row_version),
    )
    assert published.status == "active"
    with pytest.raises(BusinessRuleError):
        product_profile_service.update_product_profile_draft(
            seeded_db,
            admin,
            org.id,
            published.id,
            ProductProfileUpdate(row_version=published.row_version, product_name="Nope"),
        )
    # Correction creates a new draft version
    v2 = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="Screws lot B",
            cn_code="73181595",
            reducing_agent="Hydrogen",
            steel_mill_identification_number="TR-STEEL-002",
        ),
    )
    assert v2.version == 2
    published2 = product_profile_service.publish_product_profile(
        seeded_db,
        admin,
        org.id,
        v2.id,
        ProductProfileVersionRequest(row_version=v2.row_version),
    )
    assert published2.status == "active"
    old = product_profile_service.get_product_profile(seeded_db, admin, org.id, published.id)
    assert old.status == "superseded"
    assert old.cn_normalized_code == "73181595"


def test_invalid_draft_cannot_publish(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    draft = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(product_id=product.id, product_name="Incomplete", cn_code="73181595"),
    )
    with pytest.raises(BusinessRuleError):
        product_profile_service.publish_product_profile(
            seeded_db,
            admin,
            org.id,
            draft.id,
            ProductProfileVersionRequest(row_version=draft.row_version),
        )


def test_steel_controlled_value_and_percent_rules(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    bad_agent = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="Bad agent",
            cn_code="73181595",
            reducing_agent="Coal",
            steel_mill_identification_number="1",
        ),
    )
    assert any(i.code == "REDUCING_AGENT_INVALID" for i in bad_agent.validation_issues)

    below = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="P",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="1",
            percent_mn=Decimal("-1"),
        ),
    )
    assert any("BELOW_ZERO" in i.code for i in below.validation_issues)

    above = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="P",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="1",
            percent_mn=Decimal("100.1"),
        ),
    )
    assert any("ABOVE_100" in i.code for i in above.validation_issues)

    partial_ok = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="P",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="1",
            percent_mn=Decimal("40.12345678"),
            percent_cr=Decimal("10"),
        ),
    )
    assert partial_ok.percent_mn == Decimal("40.12345678")
    assert partial_ok.percent_other_materials is None
    assert partial_ok.classification_ready is True

    sum_over = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="P",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="1",
            percent_mn=Decimal("60"),
            percent_cr=Decimal("50"),
        ),
    )
    assert any(i.code == "PERCENTAGE_SUM_ABOVE_100" for i in sum_over.validation_issues)

    complete_bad = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="P",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="1",
            percent_mn=Decimal("20"),
            percent_cr=Decimal("20"),
            percent_ni=Decimal("20"),
            percent_other_alloys=Decimal("20"),
            percent_other_materials=Decimal("10"),
        ),
    )
    assert any(i.code == "PERCENTAGE_SUM_NOT_100" for i in complete_bad.validation_issues)

    complete_ok = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, _steel_ready_payload(product.id)
    )
    assert complete_ok.classification_ready is True


def test_draft_update_and_blank_percent_stays_null(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    draft = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="Draft",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="X",
            percent_mn=Decimal("5"),
        ),
    )
    updated = product_profile_service.update_product_profile_draft(
        seeded_db,
        admin,
        org.id,
        draft.id,
        ProductProfileUpdate(row_version=draft.row_version, percent_mn=None),
    )
    assert updated.percent_mn is None


def test_viewer_cannot_mutate_cross_org_fails(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    viewer = _viewer(seeded_db)
    product = _product(seeded_db, org.id)
    with pytest.raises(AuthorizationError):
        product_profile_service.create_product_profile(
            seeded_db, viewer, org.id, ProductProfileCreate(product_id=product.id)
        )
    created = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, ProductProfileCreate(product_id=product.id, product_name="V")
    )
    with pytest.raises((AuthorizationError, NotFoundError)):
        product_profile_service.get_product_profile(seeded_db, admin, uuid.uuid4(), created.id)


def test_production_record_cannot_link_foreign_profile(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    profile = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, _steel_ready_payload(product.id)
    )
    published = product_profile_service.publish_product_profile(
        seeded_db,
        admin,
        org.id,
        profile.id,
        ProductProfileVersionRequest(row_version=profile.row_version),
    )
    facility = seeded_db.execute(
        select(Facility).where(Facility.organization_id == org.id).limit(1)
    ).scalar_one()
    installation_service.create_installation(
        seeded_db,
        admin,
        org.id,
        InstallationCreate(
            facility_id=facility.id,
            code=f"PP-{uuid.uuid4().hex[:6]}",
            name="Profile Installation",
        ),
    )
    period = ReportingPeriod(
        organization_id=org.id,
        code=f"PP-{uuid.uuid4().hex[:6]}",
        name="Profile Period",
        period_type="custom",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        status="open",
    )
    seeded_db.add(period)
    seeded_db.flush()
    binding = period_binding_service.create_period_binding(
        seeded_db, admin, org.id, PeriodBindingCreate(reporting_period_id=period.id)
    )
    opened = period_binding_service.open_data_collection(
        seeded_db,
        admin,
        org.id,
        binding.id,
        PeriodBindingVersionRequest(row_version=binding.row_version),
    )
    installation = installation_service.list_installations(
        seeded_db, admin, org.id, page=1, page_size=50
    ).items[-1]
    # Foreign org id with this profile must fail closed.
    with pytest.raises((AuthorizationError, NotFoundError)):
        production_record_service.create_production_record(
            seeded_db,
            admin,
            uuid.uuid4(),
            opened.id,
            ProductionRecordCreate(
                installation_profile_id=installation.id,
                product_profile_version_id=published.id,
                quantity=Decimal("1"),
                unit="t",
            ),
        )


def test_profile_response_exposes_consistent_field_applicability(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id)
    profile = product_profile_service.create_product_profile(
        seeded_db,
        admin,
        org.id,
        ProductProfileCreate(
            product_id=product.id,
            product_name="Screws",
            cn_code="73181595",
            reducing_agent="Natural gas",
            steel_mill_identification_number="TR-1",
        ),
    )
    cn_detail = get_cn_code(seeded_db, admin, org.id, profile.cn_code_id)
    profile_fa = profile.field_applicability.model_dump(by_alias=True)
    cn_fa = cn_detail.field_applicability.model_dump(by_alias=True)
    assert profile_fa == cn_fa
    assert set(profile_fa) == set(FIELD_APPLICABILITY_KEYS)
    assert all(profile_fa[k] is True for k in FIELD_APPLICABILITY_KEYS)


def test_classification_ready_uses_cn_field_applicability(seeded_db) -> None:
    steel = resolve_cn_code(seeded_db, code="73181595")
    cement = resolve_cn_code(seeded_db, code="25232900")
    dataset = seeded_db.get(CbamCnCodeDataset, steel.dataset_id)
    assert dataset is not None
    ready_steel, missing_steel, _ = compute_classification_state(
        product_name="Screws",
        cn=steel,
        dataset=dataset,
        reducing_agent=None,
        steel_mill_identification_number=None,
        percent_mn=None,
        percent_cr=None,
        percent_ni=None,
        percent_other_alloys=None,
        percent_other_materials=None,
        allowed_reducing_agents={"Natural gas"},
        field_applicability=steel.field_applicability,
    )
    assert ready_steel is False
    assert {i["code"] for i in missing_steel} >= {
        "REDUCING_AGENT_REQUIRED",
        "STEEL_MILL_ID_REQUIRED",
    }
    ready_cement, missing_cement, issues_cement = compute_classification_state(
        product_name="Cement bag",
        cn=cement,
        dataset=dataset,
        reducing_agent=None,
        steel_mill_identification_number=None,
        percent_mn=None,
        percent_cr=None,
        percent_ni=None,
        percent_other_alloys=None,
        percent_other_materials=None,
        allowed_reducing_agents={"Natural gas"},
        field_applicability=cement.field_applicability,
    )
    assert ready_cement is True
    assert missing_cement == []
    assert issues_cement == []


def test_non_applicable_field_cannot_be_persisted(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id, code="CEMENT-1")
    with pytest.raises(ValidationAppError) as exc:
        product_profile_service.create_product_profile(
            seeded_db,
            admin,
            org.id,
            ProductProfileCreate(
                product_id=product.id,
                product_name="Cement",
                cn_code="25232900",
                reducing_agent="Natural gas",
            ),
        )
    assert any(d.get("code") == "REDUCING_AGENT_NOT_APPLICABLE" for d in exc.value.details)


def test_draft_cn_change_clears_stale_steel_values(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id, code="SWITCH-1")
    draft = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, _steel_ready_payload(product.id)
    )
    assert draft.reducing_agent == "Natural gas"
    assert draft.percent_mn == Decimal("40")
    # CN-only change: leftover steel values must be cleared, not left hidden.
    updated = product_profile_service.update_product_profile_draft(
        seeded_db,
        admin,
        org.id,
        draft.id,
        ProductProfileUpdate(row_version=draft.row_version, cn_code="25232900"),
    )
    assert updated.cn_normalized_code == "25232900"
    assert updated.reducing_agent is None
    assert updated.steel_mill_identification_number is None
    assert updated.percent_mn is None
    assert updated.percent_cr is None
    assert updated.percent_ni is None
    assert updated.percent_other_alloys is None
    assert updated.percent_other_materials is None
    assert all(
        updated.field_applicability.model_dump(by_alias=True)[k] is False
        for k in FIELD_APPLICABILITY_KEYS
    )
    assert updated.classification_ready is True


def test_published_profile_immutability_unchanged(seeded_db) -> None:
    org = _org(seeded_db)
    admin = _admin(seeded_db)
    product = _product(seeded_db, org.id, code="PUB-1")
    draft = product_profile_service.create_product_profile(
        seeded_db, admin, org.id, _steel_ready_payload(product.id)
    )
    published = product_profile_service.publish_product_profile(
        seeded_db,
        admin,
        org.id,
        draft.id,
        ProductProfileVersionRequest(row_version=draft.row_version),
    )
    with pytest.raises(BusinessRuleError) as exc:
        product_profile_service.update_product_profile_draft(
            seeded_db,
            admin,
            org.id,
            published.id,
            ProductProfileUpdate(row_version=published.row_version, cn_code="25232900"),
        )
    assert exc.value.details[0]["code"] == "PROFILE_NOT_DRAFT"
    still = product_profile_service.get_product_profile(seeded_db, admin, org.id, published.id)
    assert still.status == "active"
    assert still.cn_normalized_code == "73181595"
    assert still.reducing_agent == "Natural gas"
