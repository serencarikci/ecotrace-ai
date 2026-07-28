from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from ecotrace.shared.domain.schemas import CamelModel

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class OrganizationCreate(CamelModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=128)
    legal_name: str | None = Field(default=None, max_length=255)
    country_code: str = Field(min_length=2, max_length=2)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SLUG_PATTERN.match(normalized):
            raise ValueError("Slug must be lowercase alphanumeric words separated by hyphens")
        return normalized

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 2 or not code.isalpha():
            raise ValueError("Country code must be a 2-letter ISO code")
        return code

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        tz = value.strip()
        if not tz:
            raise ValueError("Timezone is required")

        if tz == "UTC" or "/" in tz or tz.startswith("Etc/") or re.match(r"^UTC[+-]\d{1,2}$", tz):
            return tz
        if re.match(r"^[A-Za-z0-9_+\-/]+$", tz):
            return tz
        raise ValueError("Invalid timezone format")


class OrganizationUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        code = value.strip().upper()
        if len(code) != 2 or not code.isalpha():
            raise ValueError("Country code must be a 2-letter ISO code")
        return code


class OrganizationResponse(CamelModel):
    id: UUID
    name: str
    slug: str
    legal_name: str | None
    country_code: str
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
