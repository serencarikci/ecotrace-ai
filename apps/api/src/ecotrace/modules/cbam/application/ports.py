from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FacilityRef:
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    timezone: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class ReportingPeriodRef:
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    status: str
    start_date: date
    end_date: date
    period_type: str | None = None


@dataclass(frozen=True, slots=True)
class ProductRef:
    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    is_active: bool
