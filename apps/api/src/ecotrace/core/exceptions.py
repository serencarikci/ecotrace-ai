from __future__ import annotations
from typing import Any

class EcoTraceError(Exception):

    def __init__(self, message: str, *, code: str='INTERNAL_ERROR', status_code: int=500, details: list[dict[str, Any]] | None=None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []

class ValidationAppError(EcoTraceError):

    def __init__(self, message: str='The request contains invalid data.', *, details: list[dict[str, Any]] | None=None) -> None:
        super().__init__(message, code='VALIDATION_ERROR', status_code=422, details=details)

class AuthenticationError(EcoTraceError):

    def __init__(self, message: str='Authentication required.', *, code: str='AUTHENTICATION_ERROR') -> None:
        super().__init__(message, code=code, status_code=401)

class AuthorizationError(EcoTraceError):

    def __init__(self, message: str='You do not have permission to perform this action.', *, code: str='AUTHORIZATION_ERROR') -> None:
        super().__init__(message, code=code, status_code=403)

class NotFoundError(EcoTraceError):

    def __init__(self, message: str='Resource not found.', *, code: str='NOT_FOUND') -> None:
        super().__init__(message, code=code, status_code=404)

class ConflictError(EcoTraceError):

    def __init__(self, message: str='Resource conflict.', *, code: str='CONFLICT', details: list[dict[str, Any]] | None=None) -> None:
        super().__init__(message, code=code, status_code=409, details=details)

class BusinessRuleError(EcoTraceError):

    def __init__(self, message: str, *, code: str='BUSINESS_RULE_ERROR', details: list[dict[str, Any]] | None=None) -> None:
        super().__init__(message, code=code, status_code=400, details=details)
