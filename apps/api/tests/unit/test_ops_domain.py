from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, ValidationAppError
from ecotrace.modules.activity_data.application.attachment_service import sanitize_original_name
from ecotrace.modules.facilities.application import facility_service
from ecotrace.modules.facilities.application.facility_service import FacilityCreate
from ecotrace.modules.identity.infrastructure.models import User
from ecotrace.modules.organizations.infrastructure.models import Organization
from ecotrace.modules.reference_data.application.unit_conversion import convert_between, get_unit
from ecotrace.modules.reference_data.infrastructure.models import Unit
from ecotrace.modules.reporting_periods.application.period_service import assert_period_writable
from ecotrace.modules.reporting_periods.infrastructure.models import ReportingPeriod


@pytest.fixture
def seeded(seeded_db: Session) -> Session:
    return seeded_db


def test_facility_coordinate_validation(seeded: Session) -> None:
    org = seeded.execute(select(Organization)).scalars().first()
    admin = seeded.execute(select(User).where(User.email == "admin@ecotrace.dev")).scalar_one()
    assert org is not None
    with pytest.raises(ValidationAppError):
        facility_service.create_facility(
            seeded,
            admin,
            org.id,
            FacilityCreate(
                code="BAD-LAT",
                name="Bad",
                facility_type="office",
                country_code="TR",
                city="Izmir",
                timezone="Europe/Istanbul",
                latitude=Decimal("95"),
                longitude=Decimal("27"),
            ),
        )


def test_facility_date_validation(seeded: Session) -> None:
    org = seeded.execute(select(Organization)).scalars().first()
    admin = seeded.execute(select(User).where(User.email == "admin@ecotrace.dev")).scalar_one()
    assert org is not None
    with pytest.raises(ValidationAppError):
        facility_service.create_facility(
            seeded,
            admin,
            org.id,
            FacilityCreate(
                code="BAD-DATE",
                name="Bad dates",
                facility_type="office",
                country_code="TR",
                city="Izmir",
                timezone="Europe/Istanbul",
                operational_start_date=date(2024, 6, 1),
                operational_end_date=date(2024, 1, 1),
            ),
        )


def test_unit_conversion(seeded: Session) -> None:
    kwh = get_unit(seeded, "kWh")
    mwh = get_unit(seeded, "MWh")
    result = convert_between(Decimal("2"), mwh, kwh)
    assert result == Decimal("2000.0000")


def test_sanitize_attachment_name() -> None:
    assert sanitize_original_name("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_original_name("invoice (1).PDF") == "invoice_1_.PDF"
    with pytest.raises(ValidationAppError):
        sanitize_original_name("..")


def test_locked_period_rejects_writes(seeded: Session) -> None:
    period = ReportingPeriod(
        organization_id=seeded.execute(select(Organization.id)).scalar_one(),
        code="LOCK-TEST",
        name="Locked",
        period_type="monthly",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        status="locked",
    )
    seeded.add(period)
    seeded.flush()
    with pytest.raises(BusinessRuleError):
        assert_period_writable(period)


def test_seed_units_idempotent(seeded: Session) -> None:
    from ecotrace.db.seed import run_seed

    count1 = seeded.execute(select(Unit)).scalars().all()
    run_seed(seeded)
    count2 = seeded.execute(select(Unit)).scalars().all()
    assert len(count1) == len(count2)
    assert Path("/tmp").exists()
