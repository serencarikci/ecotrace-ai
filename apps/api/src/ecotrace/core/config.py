from functools import lru_cache
from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from ecotrace.core.constants import INSECURE_SECRET_DEFAULTS
from ecotrace.version import __version__
AppEnv = Literal['development', 'test', 'production']

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=False, extra='ignore')
    app_name: str = Field(default='EcoTrace AI', alias='APP_NAME')
    app_env: AppEnv = Field(default='development', alias='APP_ENV')
    app_debug: bool = Field(default=False, alias='APP_DEBUG')
    app_version: str = Field(default=__version__, alias='APP_VERSION')
    api_v1_prefix: str = Field(default='/api/v1', alias='API_V1_PREFIX')
    secret_key: str = Field(alias='SECRET_KEY')
    access_token_expire_minutes: int = Field(default=15, alias='ACCESS_TOKEN_EXPIRE_MINUTES', ge=1)
    refresh_token_expire_days: int = Field(default=7, alias='REFRESH_TOKEN_EXPIRE_DAYS', ge=1)
    postgres_host: str = Field(default='localhost', alias='POSTGRES_HOST')
    postgres_port: int = Field(default=5432, alias='POSTGRES_PORT')
    postgres_db: str = Field(default='ecotrace', alias='POSTGRES_DB')
    postgres_user: str = Field(default='ecotrace', alias='POSTGRES_USER')
    postgres_password: str = Field(default='ecotrace', alias='POSTGRES_PASSWORD')
    database_url: str | None = Field(default=None, alias='DATABASE_URL')
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ['http://localhost:4200'], alias='CORS_ALLOWED_ORIGINS')
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')
    initial_admin_email: str = Field(default='admin@ecotrace.dev', alias='INITIAL_ADMIN_EMAIL')
    initial_admin_password: str = Field(alias='INITIAL_ADMIN_PASSWORD')
    initial_admin_full_name: str = Field(default='EcoTrace Admin', alias='INITIAL_ADMIN_FULL_NAME')
    demo_org_admin_email: str = Field(default='orgadmin@ecotrace.dev', alias='DEMO_ORG_ADMIN_EMAIL')
    demo_org_admin_password: str = Field(default='EcoTraceOrgAdmin!2024', alias='DEMO_ORG_ADMIN_PASSWORD')
    demo_analyst_email: str = Field(default='analyst@ecotrace.dev', alias='DEMO_ANALYST_EMAIL')
    demo_analyst_password: str = Field(default='EcoTraceAnalyst!2024', alias='DEMO_ANALYST_PASSWORD')
    demo_viewer_email: str = Field(default='viewer@ecotrace.dev', alias='DEMO_VIEWER_EMAIL')
    demo_viewer_password: str = Field(default='EcoTraceViewer!2024', alias='DEMO_VIEWER_PASSWORD')
    public_app_base_url: str = Field(default='http://localhost:4200', alias='PUBLIC_APP_BASE_URL')
    attachment_storage_path: str = Field(default='/data/attachments', alias='ATTACHMENT_STORAGE_PATH')
    max_attachment_size_mb: int = Field(default=10, alias='MAX_ATTACHMENT_SIZE_MB', ge=1)
    max_csv_import_rows: int = Field(default=5000, alias='MAX_CSV_IMPORT_ROWS', ge=1)
    allowed_attachment_types: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ['pdf', 'csv', 'xlsx', 'png', 'jpeg', 'jpg'], alias='ALLOWED_ATTACHMENT_TYPES')
    ai_llm_provider: str = Field(default='local_grounded', alias='AI_LLM_PROVIDER')
    ai_llm_model: str = Field(default='gpt-4o-mini', alias='AI_LLM_MODEL')
    ai_llm_base_url: str | None = Field(default=None, alias='AI_LLM_BASE_URL')
    ai_llm_api_key: str | None = Field(default=None, alias='AI_LLM_API_KEY')
    ai_embedding_provider: str = Field(default='local_hash', alias='AI_EMBEDDING_PROVIDER')
    ai_embedding_model: str = Field(default='local-hash-384', alias='AI_EMBEDDING_MODEL')
    ai_embedding_api_key: str | None = Field(default=None, alias='AI_EMBEDDING_API_KEY')
    ai_embedding_dimensions: int = Field(default=384, alias='AI_EMBEDDING_DIMENSIONS', ge=32)
    ai_vector_backend: str = Field(default='pgvector', alias='AI_VECTOR_BACKEND')
    ai_reranker: str = Field(default='local_lexical', alias='AI_RERANKER')
    ai_ocr_engine: str = Field(default='tesseract', alias='AI_OCR_ENGINE')
    ai_chunk_size: int = Field(default=800, alias='AI_CHUNK_SIZE', ge=100)
    ai_chunk_overlap: int = Field(default=120, alias='AI_CHUNK_OVERLAP', ge=0)
    ai_chunking_strategy: str = Field(default='markdown', alias='AI_CHUNKING_STRATEGY')
    ai_temperature: float = Field(default=0.1, alias='AI_TEMPERATURE', ge=0.0, le=2.0)
    ai_max_tokens: int = Field(default=1200, alias='AI_MAX_TOKENS', ge=64)
    ai_top_p: float = Field(default=0.95, alias='AI_TOP_P', ge=0.0, le=1.0)
    ai_retrieval_top_k: int = Field(default=12, alias='AI_RETRIEVAL_TOP_K', ge=1, le=50)
    ai_citation_mode: str = Field(default='required', alias='AI_CITATION_MODE')
    ai_enable_response_cache: bool = Field(default=True, alias='AI_ENABLE_RESPONSE_CACHE')
    ai_monthly_budget_usd: float | None = Field(default=None, alias='AI_MONTHLY_BUDGET_USD')
    knowledge_storage_path: str = Field(default='/data/knowledge', alias='KNOWLEDGE_STORAGE_PATH')
    max_knowledge_document_mb: int = Field(default=25, alias='MAX_KNOWLEDGE_DOCUMENT_MB', ge=1)
    scheduler_enabled: bool = Field(default=True, alias='SCHEDULER_ENABLED')
    scheduler_poll_seconds: int = Field(default=30, alias='SCHEDULER_POLL_SECONDS', ge=5)
    scheduler_misfire_grace_seconds: int = Field(default=300, alias='SCHEDULER_MISFIRE_GRACE_SECONDS', ge=0)
    agent_max_tool_calls: int = Field(default=12, alias='AGENT_MAX_TOOL_CALLS', ge=1)
    agent_max_execution_seconds: int = Field(default=120, alias='AGENT_MAX_EXECUTION_SECONDS', ge=10)
    agent_max_tokens: int = Field(default=2000, alias='AGENT_MAX_TOKENS', ge=64)
    job_max_attempts: int = Field(default=3, alias='JOB_MAX_ATTEMPTS', ge=1)
    report_storage_path: str = Field(default='/data/reports', alias='REPORT_STORAGE_PATH')
    backup_storage_path: str = Field(default='/data/backups', alias='BACKUP_STORAGE_PATH')
    trusted_hosts: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ['localhost', '127.0.0.1'], alias='TRUSTED_HOSTS')
    enable_hsts: bool = Field(default=False, alias='ENABLE_HSTS')
    enable_metrics: bool = Field(default=True, alias='ENABLE_METRICS')
    login_max_failures: int = Field(default=8, alias='LOGIN_MAX_FAILURES', ge=1)
    login_lockout_minutes: int = Field(default=15, alias='LOGIN_LOCKOUT_MINUTES', ge=1)
    retention_days_notifications: int = Field(default=90, alias='RETENTION_DAYS_NOTIFICATIONS', ge=1)
    retention_days_job_details: int = Field(default=180, alias='RETENTION_DAYS_JOB_DETAILS', ge=1)
    retention_days_agent_executions: int = Field(default=180, alias='RETENTION_DAYS_AGENT_EXECUTIONS', ge=1)
    smtp_enabled: bool = Field(default=False, alias='SMTP_ENABLED')
    smtp_host: str | None = Field(default=None, alias='SMTP_HOST')
    smtp_port: int = Field(default=587, alias='SMTP_PORT')
    smtp_from: str | None = Field(default=None, alias='SMTP_FROM')
    public_api_base_url: str = Field(default='http://localhost:8000', alias='PUBLIC_API_BASE_URL')
    build_commit: str | None = Field(default=None, alias='BUILD_COMMIT')
    build_timestamp: str | None = Field(default=None, alias='BUILD_TIMESTAMP')

    @field_validator('trusted_hosts', mode='before')
    @classmethod
    def parse_trusted_hosts(cls, value: object) -> list[str]:
        if isinstance(value, str):
            items = [item.strip() for item in value.split(',') if item.strip()]
            return items or ['localhost', '127.0.0.1']
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError('TRUSTED_HOSTS must be a comma-separated string or list')

    @field_validator('cors_allowed_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            items = [item.strip() for item in value.split(',') if item.strip()]
            return items or ['http://localhost:4200']
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError('CORS_ALLOWED_ORIGINS must be a comma-separated string or list')

    @field_validator('allowed_attachment_types', mode='before')
    @classmethod
    def parse_attachment_types(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(',') if item.strip()]
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        raise TypeError('ALLOWED_ATTACHMENT_TYPES must be a comma-separated string or list')

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters')
        return value

    @model_validator(mode='after')
    def validate_production_secrets(self) -> 'Settings':
        if self.app_env == 'production':
            lowered = self.secret_key.lower()
            if any((default in lowered for default in INSECURE_SECRET_DEFAULTS)):
                raise ValueError('SECRET_KEY uses an insecure default and is not allowed in production')
            if self.app_debug:
                raise ValueError('APP_DEBUG must be false in production')
            if len(self.secret_key) < 48:
                raise ValueError('SECRET_KEY must be at least 48 characters in production')
            if 'localhost' in self.cors_allowed_origins and self.enable_hsts:
                raise ValueError('Production HSTS with localhost CORS origins is unsafe')
        return self

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return f'postgresql+psycopg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'

    @property
    def is_production(self) -> bool:
        return self.app_env == 'production'

    @property
    def is_test(self) -> bool:
        return self.app_env == 'test'

@lru_cache
def get_settings() -> Settings:
    return Settings()

def reset_settings_cache() -> None:
    get_settings.cache_clear()
