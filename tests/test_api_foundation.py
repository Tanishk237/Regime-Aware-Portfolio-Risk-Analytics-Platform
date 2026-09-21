import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.errors import AppError
from src.api.main import create_app
from src.config.settings import Settings
from src.database.session import build_engine


def build_client() -> TestClient:
    database_path = Path(tempfile.mkdtemp(prefix="latent-api-test-")) / "api.db"
    settings = Settings(
        app_name="Regime Test API",
        app_version="9.9.9",
        environment="test",
        api_prefix="/api/v1",
        cors_origins=["http://localhost:3000"],
        database_url=f"sqlite:///{database_path}",
        run_migrations_on_startup=True,
    )

    return TestClient(
        create_app(settings)
    )


def test_health_endpoint():
    with build_client() as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "ok"
    assert payload["service"] == "Regime Test API"
    assert payload["environment"] == "test"
    assert payload["database"] == "sqlite"
    assert "timestamp" in payload
    assert response.headers["cache-control"] == "no-store"


def test_readiness_confirms_database_and_migrations():
    with build_client() as client:
        response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "sqlite"
    assert response.json()["migration"] == "0010_add_user_token_version"


def test_version_endpoint():
    client = build_client()

    response = client.get("/api/v1/version")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "success": True,
        "service": "Regime Test API",
        "version": "9.9.9",
        "api_prefix": "/api/v1",
        "environment": "test",
    }


def test_not_found_uses_standard_error_shape():
    client = build_client()

    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {
            "code": "HTTP_ERROR",
            "message": "Not Found",
            "details": None,
        },
    }


def test_application_errors_use_standard_error_shape():
    settings = Settings(environment="test")
    app = create_app(settings)
    router = APIRouter()

    @router.get("/boom")
    def boom():
        raise AppError(
            "Controlled failure.",
            code="CONTROLLED_FAILURE",
            status_code=409,
            details={"field": "value"},
        )

    app.include_router(router, prefix=settings.api_prefix)
    client = TestClient(app)

    response = client.get("/api/v1/boom")

    assert response.status_code == 409
    assert response.json() == {
        "success": False,
        "error": {
            "code": "CONTROLLED_FAILURE",
            "message": "Controlled failure.",
            "details": {"field": "value"},
        },
    }


def test_cors_allows_configured_frontend_origin():
    client = build_client()

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_deployment_lists_accept_json_or_comma_separated_values():
    json_settings = Settings(
        environment="test",
        cors_origins='["https://latent.example"]',
        trusted_hosts='["latent.example"]',
        nvidia_fallback_models='["model-a", "model-b"]',
        market_data_refresh_symbols="",
    )
    comma_settings = Settings(
        environment="test",
        cors_origins="https://one.example, https://two.example",
        trusted_hosts="one.example,two.example",
    )

    assert json_settings.cors_origins == ["https://latent.example"]
    assert json_settings.trusted_hosts == ["latent.example"]
    assert json_settings.nvidia_fallback_models == ["model-a", "model-b"]
    assert json_settings.market_data_refresh_symbols == []
    assert comma_settings.cors_origins == [
        "https://one.example",
        "https://two.example",
    ]
    assert comma_settings.trusted_hosts == ["one.example", "two.example"]


def test_staging_rejects_unsafe_deployment_defaults():
    with pytest.raises(ValidationError, match="AUTH_SECRET_KEY must be changed in staging"):
        Settings(
            environment="staging",
            database_url="sqlite:///./data/staging.db",
        )


def test_staging_accepts_hardened_postgresql_configuration():
    settings = Settings(
        environment="staging",
        database_url="postgresql+psycopg://latent:secret@db.example.com:5432/latent",
        database_ssl_mode="verify-full",
        auth_secret_key="staging-secret-with-at-least-32-characters",
        auth_cookie_secure=True,
        cors_origins=["https://app.staging.example.com"],
        trusted_hosts=["api.staging.example.com"],
        regime_runtime_fit_enabled=False,
    )

    assert settings.environment == "staging"
    assert settings.database_url.startswith("postgresql")


def test_staging_accepts_neon_tls_channel_binding():
    settings = Settings(
        environment="staging",
        database_url=(
            "postgresql+psycopg://latent:secret@db.example.com:5432/latent"
            "?sslmode=require&channel_binding=require"
        ),
        database_ssl_mode="require",
        auth_secret_key="staging-secret-with-at-least-32-characters",
        auth_cookie_secure=True,
        cors_origins=["https://app.staging.example.com"],
        trusted_hosts=["api.staging.example.com"],
        regime_runtime_fit_enabled=False,
    )

    assert settings.database_ssl_mode == "require"


def test_migration_url_defaults_to_runtime_database_url():
    settings = Settings(
        environment="test",
        database_url="sqlite:///./data/test.db",
    )

    assert settings.effective_migration_database_url == settings.database_url


def test_staging_can_use_direct_migration_url_with_pooled_runtime_url():
    settings = Settings(
        environment="staging",
        database_url=(
            "postgresql+psycopg://latent:secret@db-pooler.example.com:5432/latent"
            "?sslmode=require&channel_binding=require"
        ),
        migration_database_url=(
            "postgresql+psycopg://latent:secret@db.example.com:5432/latent"
            "?sslmode=require&channel_binding=require"
        ),
        database_ssl_mode="require",
        auth_secret_key="staging-secret-with-at-least-32-characters",
        auth_cookie_secure=True,
        cors_origins=["https://app.staging.example.com"],
        trusted_hosts=["api.staging.example.com"],
        regime_runtime_fit_enabled=False,
    )

    assert "-pooler" in settings.database_url
    assert "-pooler" not in settings.effective_migration_database_url


def test_staging_rejects_tls_without_verification_or_channel_binding():
    with pytest.raises(ValidationError, match="channel_binding=require"):
        Settings(
            environment="staging",
            database_url=(
                "postgresql+psycopg://latent:secret@db.example.com:5432/latent"
                "?sslmode=require"
            ),
            database_ssl_mode="require",
            auth_secret_key="staging-secret-with-at-least-32-characters",
            auth_cookie_secure=True,
            cors_origins=["https://app.staging.example.com"],
            trusted_hosts=["api.staging.example.com"],
            regime_runtime_fit_enabled=False,
        )


def test_large_responses_are_compressed_and_timed():
    settings = Settings(
        environment="test",
        database_url="sqlite://",
        run_migrations_on_startup=True,
        gzip_minimum_size_bytes=256,
    )
    app = create_app(settings)

    @app.get("/large-response")
    def large_response():
        return JSONResponse({"payload": "x" * 5000})

    response = TestClient(app).get(
        "/large-response",
        headers={"Accept-Encoding": "gzip"},
    )

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert response.headers["server-timing"].startswith("app;dur=")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-request-id"]


def test_oversized_request_is_rejected_before_body_parsing():
    settings = Settings(
        environment="test",
        database_url="sqlite://",
        run_migrations_on_startup=True,
        csv_upload_max_bytes=512,
        request_body_max_bytes=1024,
    )
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/v1/auth/login",
            content=b"x" * 2048,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_valid_request_id_is_propagated():
    with build_client() as client:
        response = client.get(
            "/api/v1/health",
            headers={"X-Request-ID": "release-check-123"},
        )

    assert response.headers["x-request-id"] == "release-check-123"


def test_sqlite_connections_enforce_integrity_and_concurrency_pragmas(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'configured.db'}")
    try:
        with engine.connect() as connection:
            foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
            busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()
            journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
    finally:
        engine.dispose()

    assert foreign_keys == 1
    assert busy_timeout == 5000
    assert journal_mode == "wal"
