import json
import secrets
from functools import lru_cache
from typing import Annotated, List, Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _parse_string_list(value):
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        return []

    if normalized.startswith("["):
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise ValueError("Expected a JSON array or comma-separated list") from exc
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ValueError("Expected a JSON array of strings")
        return [item.strip() for item in parsed if item.strip()]

    return [item.strip() for item in normalized.split(",") if item.strip()]


def _requires_tls_channel_binding(database_url: str) -> bool:
    values = parse_qs(urlsplit(database_url).query).get("channel_binding", [])
    return any(value.lower() == "require" for value in values)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        str_strip_whitespace=True,
    )

    app_name: str = "Latent"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = False
    database_url: str = "postgresql+psycopg://latent:latent@localhost:5432/latent"
    migration_database_url: str = Field(default="", repr=False)
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=300)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86_400)
    database_ssl_mode: str = "disable"
    create_db_on_startup: bool = False
    run_migrations_on_startup: bool = False
    default_user_email: str = "local@example.com"
    default_user_name: str = "Local User"
    auth_secret_key: str = Field(default="", repr=False)
    access_token_expire_minutes: int = 60 * 24
    guest_session_expire_minutes: int = 60 * 12
    guest_data_retention_hours: int = 24
    guest_cleanup_interval_seconds: int = Field(default=3600, ge=60, le=86_400)
    csv_upload_max_bytes: int = Field(default=5 * 1024 * 1024, gt=0)
    request_body_max_bytes: int = Field(default=6 * 1024 * 1024, gt=0)
    csv_upload_max_rows: int = Field(default=10_000, ge=1, le=100_000)
    csv_upload_max_columns: int = Field(default=30, ge=4, le=200)
    csv_upload_max_field_characters: int = Field(default=2_000, ge=64, le=100_000)
    csv_upload_max_cells: int = Field(default=200_000, ge=4, le=2_000_000)
    csv_resolution_max_changes: int = Field(default=2_000, ge=1, le=50_000)
    csv_upload_rate_limit: int = Field(default=20, ge=1, le=10_000)
    csv_upload_ip_rate_limit: int = Field(default=50, ge=1, le=100_000)
    csv_upload_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    portfolio_max_per_user: int = Field(default=50, ge=1, le=1_000)
    portfolio_max_per_guest: int = Field(default=5, ge=1, le=100)
    portfolio_max_trades: int = Field(default=10_000, ge=1, le=100_000)
    portfolio_workload_rate_limit: int = Field(default=240, ge=1, le=100_000)
    portfolio_guest_workload_rate_limit: int = Field(default=60, ge=1, le=100_000)
    portfolio_ip_workload_rate_limit: int = Field(default=500, ge=1, le=100_000)
    portfolio_workload_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    auth_cookie_name: str = "rapra_access_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    fii_dii_csv_path: str = "data/external/fii_dii.csv"
    market_data_provider: str = "yahoo"
    market_data_cache_ttl_seconds: int = 900
    instrument_metadata_ttl_days: int = Field(default=30, ge=1, le=365)
    market_data_provider_retries: int = 3
    market_data_provider_retry_backoff_seconds: float = 0.25
    market_data_max_tickers_per_request: int = Field(default=20, ge=1, le=100)
    market_data_max_history_days: int = Field(default=3650, ge=30, le=20_000)
    market_public_rate_limit: int = Field(default=30, ge=1, le=10_000)
    market_user_rate_limit: int = Field(default=240, ge=1, le=100_000)
    market_ip_rate_limit: int = Field(default=500, ge=1, le=100_000)
    market_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    market_data_refresh_enabled: bool = False
    market_data_refresh_interval_seconds: int = 900
    market_data_refresh_symbols: Annotated[List[str], NoDecode] = Field(default_factory=list)
    regime_model_dir: str = "models"
    regime_runtime_fit_enabled: bool = True
    regime_max_observations: int = Field(default=1_500, ge=50, le=20_000)
    regime_validation_report_path: str = "models/regime_validation_report.json"
    require_validated_regime_model: bool = False
    intelligence_cache_ttl_seconds: int = Field(default=60, ge=0, le=3600)
    nvidia_api_key: str = Field(default="", repr=False)
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    nvidia_fallback_models: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "z-ai/glm-5.3-flash",
            "z-ai/glm-5.3",
        ]
    )
    ai_max_output_tokens: int = Field(default=700, ge=128, le=4096)
    ai_history_messages: int = Field(default=6, ge=0, le=20)
    ai_retrieval_top_k: int = Field(default=4, ge=2, le=10)
    ai_retrieval_character_budget: int = Field(default=6000, ge=1200, le=20_000)
    gzip_minimum_size_bytes: int = Field(default=1000, ge=256, le=1_000_000)
    slow_request_threshold_ms: int = Field(default=1500, ge=100, le=60_000)
    api_docs_enabled: bool = True
    sentry_dsn: str = Field(default="", repr=False)
    sentry_traces_sample_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    auth_login_rate_limit: int = Field(default=10, ge=1, le=1000)
    auth_account_login_rate_limit: int = Field(default=20, ge=1, le=10_000)
    auth_signup_rate_limit: int = Field(default=5, ge=1, le=1000)
    auth_sensitive_action_rate_limit: int = Field(default=5, ge=1, le=1000)
    auth_sensitive_action_ip_rate_limit: int = Field(default=20, ge=1, le=10_000)
    guest_rate_limit: int = Field(default=10, ge=1, le=1000)
    ai_rate_limit: int = Field(default=30, ge=1, le=10_000)
    ai_guest_rate_limit: int = Field(default=10, ge=1, le=10_000)
    ai_ip_rate_limit: int = Field(default=100, ge=1, le=100_000)
    analytics_rate_limit: int = Field(default=120, ge=1, le=100_000)
    analytics_guest_rate_limit: int = Field(default=30, ge=1, le=100_000)
    analytics_ip_rate_limit: int = Field(default=300, ge=1, le=100_000)
    auth_rate_limit_window_seconds: int = Field(default=60, ge=10, le=86_400)
    auth_account_login_rate_limit_window_seconds: int = Field(
        default=900, ge=60, le=86_400
    )
    auth_sensitive_action_rate_limit_window_seconds: int = Field(
        default=3600, ge=60, le=86_400
    )
    signup_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    ai_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    analytics_rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86_400)
    trusted_hosts: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        return _parse_string_list(value)

    @field_validator("nvidia_fallback_models", mode="before")
    @classmethod
    def parse_nvidia_fallback_models(cls, value):
        return _parse_string_list(value)

    @field_validator("market_data_refresh_symbols", mode="before")
    @classmethod
    def parse_market_data_refresh_symbols(cls, value):
        return _parse_string_list(value)

    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def parse_trusted_hosts(cls, value):
        return _parse_string_list(value)

    @field_validator("database_ssl_mode")
    @classmethod
    def validate_database_ssl_mode(cls, value):
        normalized = value.lower()
        if normalized not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
            raise ValueError("DATABASE_SSL_MODE is not a supported PostgreSQL sslmode")
        return normalized

    @field_validator("auth_cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value):
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("auth_cookie_samesite must be one of: lax, strict, none")
        return normalized

    @model_validator(mode="after")
    def validate_deployment_security(self):
        if self.request_body_max_bytes < self.csv_upload_max_bytes:
            raise ValueError("REQUEST_BODY_MAX_BYTES must be at least CSV_UPLOAD_MAX_BYTES")
        if self.environment.lower() in {"staging", "production"}:
            environment_name = self.environment.lower()
            normalized_secret = self.auth_secret_key.strip().lower()
            if normalized_secret == "change-me-in-production" or normalized_secret.startswith(
                ("replace-with", "example-", "changeme")
            ):
                raise ValueError(f"AUTH_SECRET_KEY must be changed in {environment_name}")
            if len(self.auth_secret_key) < 32:
                raise ValueError(
                    f"AUTH_SECRET_KEY must be at least 32 characters in {environment_name}"
                )
            if "*" in self.cors_origins:
                raise ValueError(f"CORS_ORIGINS cannot contain '*' in {environment_name}")
            if "*" in self.trusted_hosts or not self.trusted_hosts:
                raise ValueError(
                    f"TRUSTED_HOSTS must contain explicit hosts in {environment_name}"
                )
            if not self.auth_cookie_secure:
                raise ValueError(f"AUTH_COOKIE_SECURE must be true in {environment_name}")
            if self.auth_cookie_samesite == "none":
                raise ValueError(
                    f"AUTH_COOKIE_SAMESITE cannot be 'none' in {environment_name}"
                )
            if not self.database_url.startswith("postgresql"):
                raise ValueError(f"DATABASE_URL must use PostgreSQL in {environment_name}")
            if self.migration_database_url and not self.migration_database_url.startswith(
                "postgresql"
            ):
                raise ValueError(
                    f"MIGRATION_DATABASE_URL must use PostgreSQL in {environment_name}"
                )
            if self.market_data_provider.lower() == "test-fixture":
                raise ValueError(
                    f"MARKET_DATA_PROVIDER cannot use test-fixture in {environment_name}"
                )
            has_verified_tls = self.database_ssl_mode == "verify-full"
            runtime_has_bound_tls = (
                self.database_ssl_mode == "require"
                and _requires_tls_channel_binding(self.database_url)
            )
            migration_has_bound_tls = (
                self.database_ssl_mode == "require"
                and _requires_tls_channel_binding(
                    self.effective_migration_database_url
                )
            )
            if not (
                has_verified_tls
                or (runtime_has_bound_tls and migration_has_bound_tls)
            ):
                raise ValueError(
                    "Runtime and migration PostgreSQL TLS require "
                    "DATABASE_SSL_MODE=verify-full or "
                    "DATABASE_SSL_MODE=require with channel_binding=require "
                    f"in {environment_name}"
                )
            if self.regime_runtime_fit_enabled:
                raise ValueError(
                    f"REGIME_RUNTIME_FIT_ENABLED must be false in {environment_name}"
                )
            if self.nvidia_api_key and not self.nvidia_base_url.startswith("https://"):
                raise ValueError(f"NVIDIA_BASE_URL must use HTTPS in {environment_name}")
        elif not self.auth_secret_key:
            # Local and test instances get an unguessable, process-scoped key by default.
            self.auth_secret_key = secrets.token_urlsafe(32)
        return self

    @property
    def effective_migration_database_url(self) -> str:
        return self.migration_database_url or self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
