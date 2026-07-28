from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from ecotrace.core.constants import INSECURE_SECRET_DEFAULTS
from ecotrace.version import __version__

AppEnv = Literal["development", "test", "production"]


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="EcoTrace AI", alias="APP_NAME")
    app_env: AppEnv = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_version: str = Field(default=__version__, alias="APP_VERSION")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES", ge=1)
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS", ge=1)

    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="ecotrace", alias="POSTGRES_DB")
    postgres_user: str = Field(default="ecotrace", alias="POSTGRES_USER")
    postgres_password: str = Field(default="ecotrace", alias="POSTGRES_PASSWORD")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:4200"],
        alias="CORS_ALLOWED_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    initial_admin_email: str = Field(default="admin@ecotrace.dev", alias="INITIAL_ADMIN_EMAIL")
    initial_admin_password: str = Field(alias="INITIAL_ADMIN_PASSWORD")
    initial_admin_full_name: str = Field(default="EcoTrace Admin", alias="INITIAL_ADMIN_FULL_NAME")

    demo_org_admin_email: str = Field(default="orgadmin@ecotrace.dev", alias="DEMO_ORG_ADMIN_EMAIL")
    demo_org_admin_password: str = Field(
        default="EcoTraceOrgAdmin!2024", alias="DEMO_ORG_ADMIN_PASSWORD"
    )
    demo_analyst_email: str = Field(default="analyst@ecotrace.dev", alias="DEMO_ANALYST_EMAIL")
    demo_analyst_password: str = Field(
        default="EcoTraceAnalyst!2024", alias="DEMO_ANALYST_PASSWORD"
    )
    demo_viewer_email: str = Field(default="viewer@ecotrace.dev", alias="DEMO_VIEWER_EMAIL")
    demo_viewer_password: str = Field(default="EcoTraceViewer!2024", alias="DEMO_VIEWER_PASSWORD")

    attachment_storage_path: str = Field(
        default="/data/attachments", alias="ATTACHMENT_STORAGE_PATH"
    )
    max_attachment_size_mb: int = Field(default=10, alias="MAX_ATTACHMENT_SIZE_MB", ge=1)
    max_csv_import_rows: int = Field(default=5000, alias="MAX_CSV_IMPORT_ROWS", ge=1)
    allowed_attachment_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["pdf", "csv", "xlsx", "png", "jpeg", "jpg"],
        alias="ALLOWED_ATTACHMENT_TYPES",
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",") if item.strip()]
            return items or ["http://localhost:4200"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("CORS_ALLOWED_ORIGINS must be a comma-separated string or list")

    @field_validator("allowed_attachment_types", mode="before")
    @classmethod
    def parse_attachment_types(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip().lower() for item in value if str(item).strip()]
        raise TypeError("ALLOWED_ATTACHMENT_TYPES must be a comma-separated string or list")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key_length(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            lowered = self.secret_key.lower()
            if any(default in lowered for default in INSECURE_SECRET_DEFAULTS):
                raise ValueError(
                    "SECRET_KEY uses an insecure default and is not allowed in production"
                )
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production")
        return self

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
