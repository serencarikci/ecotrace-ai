from typing import Final
ROLE_SYSTEM_ADMIN: Final[str] = 'system_admin'
ROLE_ORGANIZATION_ADMIN: Final[str] = 'organization_admin'
ROLE_SUSTAINABILITY_MANAGER: Final[str] = 'sustainability_manager'
ROLE_ANALYST: Final[str] = 'analyst'
ROLE_VIEWER: Final[str] = 'viewer'
DEFAULT_ROLES: Final[tuple[tuple[str, str, str], ...]] = ((ROLE_SYSTEM_ADMIN, 'System Administrator', 'Full platform administration privileges'), (ROLE_ORGANIZATION_ADMIN, 'Organization Administrator', 'Administer a single organization'), (ROLE_SUSTAINABILITY_MANAGER, 'Sustainability Manager', 'Manage sustainability programs and reporting'), (ROLE_ANALYST, 'Analyst', 'Analyze sustainability and carbon data'), (ROLE_VIEWER, 'Viewer', 'Read-only access within an organization'))
TOKEN_TYPE_ACCESS: Final[str] = 'access'
TOKEN_TYPE_REFRESH: Final[str] = 'refresh'
REQUEST_ID_HEADER: Final[str] = 'X-Request-ID'
INSECURE_SECRET_DEFAULTS: Final[frozenset[str]] = frozenset({'change-me', 'change-me-to-a-long-random-secret-at-least-32-chars', 'secret', 'password', 'dev-secret'})
