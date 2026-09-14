from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from ecotrace.shared.domain.schemas import CamelModel


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(CamelModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshRequest(CamelModel):
    refresh_token: str


class LogoutRequest(CamelModel):
    refresh_token: str


class UserSummary(CamelModel):
    id: UUID
    email: EmailStr
    full_name: str
    roles: list[str]


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class OrganizationMembershipSummary(CamelModel):
    organization_id: UUID
    organization_name: str
    organization_slug: str
    role_code: str
    is_active: bool


class MeResponse(CamelModel):
    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_verified: bool
    roles: list[str]
    last_login_at: datetime | None = None
