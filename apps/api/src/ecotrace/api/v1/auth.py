from __future__ import annotations

from fastapi import APIRouter, status

from ecotrace.api.dependencies.auth import (
    ClientIp,
    CurrentUser,
    DbSession,
    OptionalCurrentUser,
    RequestId,
    UserAgentHeader,
)
from ecotrace.modules.identity.application import auth_service
from ecotrace.modules.identity.presentation.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MeResponse,
    OrganizationMembershipSummary,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns access and refresh tokens.",
    responses={
        401: {"description": "Invalid credentials"},
        422: {"description": "Validation error"},
    },
)
def login(
    payload: LoginRequest,
    db: DbSession,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> TokenResponse:
    return auth_service.authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh tokens",
    description="Rotate refresh token and obtain a new access token.",
)
def refresh(
    payload: RefreshRequest,
    db: DbSession,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> TokenResponse:
    return auth_service.refresh_tokens(
        db,
        refresh_token=payload.refresh_token,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout",
    description="Revoke the provided refresh token.",
)
def logout(
    payload: LogoutRequest,
    db: DbSession,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
    user: OptionalCurrentUser,
) -> None:
    actor_id = user.id if user is not None else None
    auth_service.logout(
        db,
        refresh_token=payload.refresh_token,
        actor_user_id=actor_id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout all sessions",
    description="Revoke all refresh tokens for the current user.",
)
def logout_all(
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> None:
    auth_service.logout_all(
        db,
        user_id=user.id,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Change the current user's password and revoke all refresh tokens.",
)
def change_password(
    payload: ChangePasswordRequest,
    db: DbSession,
    user: CurrentUser,
    request_id: RequestId,
    ip: ClientIp,
    user_agent: UserAgentHeader,
) -> None:
    auth_service.change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        request_id=request_id,
        ip_address=ip,
        user_agent=user_agent,
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Current user",
    tags=["Users"],
)
def me(user: CurrentUser) -> MeResponse:
    return auth_service.get_me(user)


@router.get(
    "/me/organizations",
    response_model=list[OrganizationMembershipSummary],
    summary="Current user organizations",
    tags=["Users"],
)
def my_organizations(db: DbSession, user: CurrentUser) -> list[OrganizationMembershipSummary]:
    return auth_service.list_my_organizations(db, user)
