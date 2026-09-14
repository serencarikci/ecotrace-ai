from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from ecotrace.core.exceptions import BusinessRuleError, NotFoundError, ValidationAppError
from ecotrace.modules.cbam.infrastructure.models import (
    CbamInstallationProfile,
    CbamProductProfileVersion,
    CbamReportingPeriodBinding,
)

WRITABLE_BINDING_STATUSES = frozenset({"draft", "data_collection"})
MUTATION_BLOCKED_BINDING_STATUSES = frozenset({"locked", "approved"})


def get_binding_for_org(
    db: Session, organization_id: uuid.UUID, binding_id: uuid.UUID
) -> CbamReportingPeriodBinding:
    row = db.get(CbamReportingPeriodBinding, binding_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("CBAM reporting period binding not found.")
    return row


def require_writable_binding(binding: CbamReportingPeriodBinding) -> None:
    if binding.status in MUTATION_BLOCKED_BINDING_STATUSES:
        raise BusinessRuleError(
            "Locked or approved CBAM reporting period bindings cannot accept data mutations "
            "(approve/lock deferred until D-030).",
            details=[{"code": "BLOCKED_DOMAIN", "decision": "D-030", "status": binding.status}],
        )
    if binding.status not in WRITABLE_BINDING_STATUSES:
        raise BusinessRuleError(
            "Data-collection mutations are only allowed while the period binding is "
            "draft or data_collection.",
            details=[{"code": "PERIOD_NOT_WRITABLE", "status": binding.status}],
        )


def get_installation_for_org(
    db: Session, organization_id: uuid.UUID, installation_id: uuid.UUID
) -> CbamInstallationProfile:
    row = db.get(CbamInstallationProfile, installation_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("CBAM installation profile not found.")
    return row


def require_usable_installation(installation: CbamInstallationProfile) -> None:
    if installation.status == "archived":
        raise BusinessRuleError(
            "Archived installation profiles cannot receive new or updated data-collection records."
        )


def get_product_profile_for_org(
    db: Session, organization_id: uuid.UUID, profile_id: uuid.UUID
) -> CbamProductProfileVersion:
    row = db.get(CbamProductProfileVersion, profile_id)
    if row is None or row.organization_id != organization_id:
        raise NotFoundError("CBAM product profile version not found.")
    return row


def require_positive_quantity(value: Decimal, *, field: str = "quantity") -> None:
    if value <= 0:
        raise ValidationAppError(
            f"{field} must be greater than zero.",
            details=[{"field": field, "message": "Must be > 0."}],
        )


def require_non_negative(value: Decimal, *, field: str) -> None:
    if value < 0:
        raise ValidationAppError(
            f"{field} cannot be negative.",
            details=[{"field": field, "message": "Must be >= 0."}],
        )


def validate_optional_date_range(period_start: date | None, period_end: date | None) -> None:
    if period_start and period_end and period_end < period_start:
        raise ValidationAppError("periodEnd must be on or after periodStart.")
