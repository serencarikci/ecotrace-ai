from __future__ import annotations
import uuid
from collections.abc import Callable
from typing import Annotated
from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from ecotrace.core.constants import ROLE_SYSTEM_ADMIN
from ecotrace.core.database import get_db
from ecotrace.core.exceptions import AuthenticationError, AuthorizationError
from ecotrace.modules.identity.application import auth_service
from ecotrace.modules.identity.infrastructure.models import User
bearer_scheme = HTTPBearer(auto_error=False)

def get_request_id(request: Request) -> str | None:
    return getattr(request.state, 'request_id', None)

def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    if request.client:
        return request.client.host
    return None

def get_user_agent(request: Request) -> str | None:
    return request.headers.get('User-Agent')

def get_optional_current_user(request: Request, db: Annotated[Session, Depends(get_db)], credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> User | None:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        return None
    try:
        user = auth_service.resolve_user_from_access_token(db, credentials.credentials)
    except AuthenticationError:
        return None
    request.state.user_id = str(user.id)
    return user

def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)], credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> User:
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise AuthenticationError()
    user = auth_service.resolve_user_from_access_token(db, credentials.credentials)
    request.state.user_id = str(user.id)
    return user

def get_current_active_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    return auth_service.require_active_user(user)

def require_system_admin(user: Annotated[User, Depends(get_current_active_user)]) -> User:
    if not auth_service.user_has_role(user, ROLE_SYSTEM_ADMIN):
        raise AuthorizationError('System administrator role required.')
    return user

def require_roles(*role_codes: str) -> Callable[..., User]:

    def _dependency(user: Annotated[User, Depends(get_current_active_user)]) -> User:
        auth_service.require_roles(user, *role_codes)
        return user
    return _dependency
CurrentUser = Annotated[User, Depends(get_current_active_user)]
OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
RequestId = Annotated[str | None, Depends(get_request_id)]
ClientIp = Annotated[str | None, Depends(get_client_ip)]
UserAgentHeader = Annotated[str | None, Depends(get_user_agent)]
OptionalOrgId = Annotated[uuid.UUID | None, Header(alias='X-Organization-Id')]
