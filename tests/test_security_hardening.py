from datetime import timedelta
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.auth import create_access_token
from src.config.settings import Settings
from src.utils.logging import configure_sentry


def _client(tmp_path, **overrides) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'security.db'}",
        run_migrations_on_startup=True,
        auth_secret_key="security-hardening-test-secret",
        **overrides,
    )
    return TestClient(create_app(settings))


def _production_settings(**overrides) -> dict:
    values = {
        "environment": "production",
        "database_url": "postgresql+psycopg://user:pass@db.example.com/latent",
        "database_ssl_mode": "verify-full",
        "auth_secret_key": "a-production-secret-with-at-least-32-characters",
        "auth_cookie_secure": True,
        "auth_cookie_samesite": "lax",
        "cors_origins": ["https://app.example.com"],
        "trusted_hosts": ["api.example.com"],
        "regime_runtime_fit_enabled": False,
    }
    values.update(overrides)
    return values


def test_environment_name_is_fail_closed():
    with pytest.raises(ValidationError, match="environment"):
        Settings(environment="prodution")


def test_production_requires_explicit_auth_secret():
    with pytest.raises(ValidationError, match="AUTH_SECRET_KEY"):
        Settings(**_production_settings(auth_secret_key=""))


def test_production_rejects_cross_site_auth_cookie():
    with pytest.raises(ValidationError, match="AUTH_COOKIE_SAMESITE"):
        Settings(**_production_settings(auth_cookie_samesite="none"))


def test_migration_connection_must_match_runtime_tls_guarantee():
    with pytest.raises(ValidationError, match="migration PostgreSQL TLS"):
        Settings(
            **_production_settings(
                database_url=(
                    "postgresql+psycopg://user:pass@pooler.example.com/latent"
                    "?sslmode=require&channel_binding=require"
                ),
                migration_database_url=(
                    "postgresql+psycopg://user:pass@direct.example.com/latent"
                    "?sslmode=require"
                ),
                database_ssl_mode="require",
            )
        )


def test_sentry_does_not_capture_locals_or_request_bodies(monkeypatch):
    captured = {}

    def fake_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("sentry_sdk.init", fake_init)
    configure_sentry(
        "https://public@example.invalid/1",
        environment="test",
        release="test",
        traces_sample_rate=0.0,
    )

    assert captured["include_local_variables"] is False
    assert captured["max_request_body_size"] == "never"
    assert captured["send_default_pii"] is False


def test_login_is_throttled_per_account_identifier(tmp_path):
    with _client(
        tmp_path,
        auth_login_rate_limit=100,
        auth_account_login_rate_limit=2,
        auth_account_login_rate_limit_window_seconds=600,
    ) as client:
        for _ in range(2):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "target@example.com", "password": "wrong"},
            )
            assert response.status_code == 401

        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "target@example.com", "password": "wrong"},
        )

    assert limited.status_code == 429
    assert limited.json()["error"]["details"]["bucket"] == "auth:login:account"


def test_account_deletion_password_attempts_are_throttled(tmp_path):
    with _client(
        tmp_path,
        auth_sensitive_action_rate_limit=2,
        auth_sensitive_action_ip_rate_limit=100,
    ) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "delete-rate@example.com",
                "password": "strong-password",
                "full_name": "Delete Rate",
            },
        )
        assert signup.status_code == 201

        for _ in range(2):
            response = client.request(
                "DELETE",
                "/api/v1/auth/account",
                json={"password": "wrong-password", "confirmation": "DELETE"},
            )
            assert response.status_code == 401

        limited = client.request(
            "DELETE",
            "/api/v1/auth/account",
            json={"password": "wrong-password", "confirmation": "DELETE"},
        )

    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"


def test_profile_rejects_oversized_restrictions(tmp_path):
    with _client(tmp_path) as client:
        assert client.post(
            "/api/v1/auth/signup",
            json={
                "email": "profile@example.com",
                "password": "strong-password",
                "full_name": "Profile User",
            },
        ).status_code == 201

        response = client.put(
            "/api/v1/intelligence/profile",
            json={"restrictions": ["x" * 201]},
        )

    assert response.status_code == 422


def test_guest_claim_cannot_be_used_for_registered_account(tmp_path):
    secret = "security-hardening-test-secret"
    with _client(tmp_path) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "registered@example.com",
                "password": "strong-password",
                "full_name": "Registered User",
            },
        )
        user_id = signup.json()["user"]["id"]
        forged = create_access_token(
            subject=str(user_id),
            secret_key=secret,
            expires_delta=timedelta(minutes=5),
            extra_claims={"guest": True, "ver": 0},
        )
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {forged}"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTH_TOKEN"
