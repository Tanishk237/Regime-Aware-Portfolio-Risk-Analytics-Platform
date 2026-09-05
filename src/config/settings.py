from functools import lru_cache
from typing import List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Latent"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/regime.db"
    create_db_on_startup: bool = False
    run_migrations_on_startup: bool = False
    default_user_email: str = "local@example.com"
    default_user_name: str = "Local User"
    auth_secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24
    auth_cookie_name: str = "rapra_access_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    fii_dii_csv_path: str = "data/external/fii_dii.csv"
    market_data_provider: str = "yahoo"
    market_data_cache_ttl_seconds: int = 900
    market_data_provider_retries: int = 3
    market_data_provider_retry_backoff_seconds: float = 0.25
    market_data_refresh_enabled: bool = False
    market_data_refresh_interval_seconds: int = 900
    market_data_refresh_symbols: List[str] = Field(default_factory=list)
    regime_model_dir: str = "models"
    cors_origins: List[str] = Field(
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
        if isinstance(value, str):
            return [
                origin.strip()
                for origin in value.split(",")
                if origin.strip()
            ]

        return value

    @field_validator("auth_cookie_samesite")
    @classmethod
    def validate_cookie_samesite(cls, value):
        normalized = value.lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("auth_cookie_samesite must be one of: lax, strict, none")
        return normalized

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.environment.lower() == "production":
            if self.auth_secret_key == "change-me-in-production":
                raise ValueError("AUTH_SECRET_KEY must be changed in production")
            if len(self.auth_secret_key) < 32:
                raise ValueError("AUTH_SECRET_KEY must be at least 32 characters in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production")
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
