from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ecotrace.core.exceptions import ValidationAppError
from ecotrace.modules.facilities.application.facility_service import _validate_facility_fields


def test_facility_validation_accepts_valid_payload() -> None:
    _validate_facility_fields(
        facility_type="manufacturing",
        country_code="tr",
        timezone="Europe/Istanbul",
        latitude=Decimal("38.4"),
        longitude=Decimal("27.1"),
        start=date(2020, 1, 1),
        end=date(2030, 1, 1),
    )


def test_facility_validation_rejects_bad_type() -> None:
    with pytest.raises(ValidationAppError):
        _validate_facility_fields(
            facility_type="spaceship",
            country_code="TR",
            timezone="UTC",
            latitude=None,
            longitude=None,
            start=None,
            end=None,
        )


def test_facility_validation_rejects_latitude() -> None:
    with pytest.raises(ValidationAppError):
        _validate_facility_fields(
            facility_type="office",
            country_code="TR",
            timezone="UTC",
            latitude=Decimal("95"),
            longitude=None,
            start=None,
            end=None,
        )


def test_facility_validation_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationAppError):
        _validate_facility_fields(
            facility_type="office",
            country_code="TR",
            timezone="UTC",
            latitude=None,
            longitude=None,
            start=date(2024, 2, 1),
            end=date(2024, 1, 1),
        )
