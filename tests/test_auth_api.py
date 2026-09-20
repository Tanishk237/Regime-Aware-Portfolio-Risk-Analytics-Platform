from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings
from src.database.models import Portfolio, Trade, User


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'auth.db'}",
        run_migrations_on_startup=True,
        auth_secret_key="test-secret",
    )
    return TestClient(create_app(settings))


def test_signup_login_me_and_protected_route_flow(tmp_path):
    with build_client(tmp_path) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "user@example.com",
                "password": "strong-password",
                "full_name": "Auth User",
            },
        )
        assert signup.status_code == 201
        payload = signup.json()
        assert payload["token_type"] == "bearer"
        assert payload["access_token"]
        assert payload["user"]["email"] == "user@example.com"
        assert "password" not in payload["user"]
        assert "rapra_access_token" in client.cookies
        assert "Max-Age" not in signup.headers["set-cookie"]

        cookie_me = client.get("/api/v1/auth/me")
        assert cookie_me.status_code == 200
        assert cookie_me.json()["email"] == "user@example.com"

        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert "rapra_access_token" not in client.cookies

        protected_without_token = client.get("/api/v1/portfolio")
        assert protected_without_token.status_code == 401
        assert protected_without_token.json()["error"]["code"] == "AUTH_REQUIRED"

        client.headers.update(
            {"Authorization": f"Bearer {payload['access_token']}"}
        )
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 401
        assert me.json()["error"]["code"] == "SESSION_REVOKED"

        client.headers.clear()
        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@example.com",
                "password": "strong-password",
            },
        )
        assert login.status_code == 200
        assert login.json()["access_token"]
        assert "rapra_access_token" in client.cookies
        assert "Max-Age" not in login.headers["set-cookie"]

        remembered_login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@example.com",
                "password": "strong-password",
                "remember_me": True,
            },
        )
        assert remembered_login.status_code == 200
        assert "Max-Age" in remembered_login.headers["set-cookie"]


def test_guest_session_uses_bearer_token_without_cookie(tmp_path):
    with build_client(tmp_path) as client:
        guest = client.post("/api/v1/auth/guest")
        assert guest.status_code == 201
        payload = guest.json()
        assert payload["token_type"] == "bearer"
        assert payload["access_token"]
        assert payload["user"]["email"].endswith("@guest.latent.local")
        assert payload["user"]["full_name"] == "Guest"
        assert "rapra_access_token" not in client.cookies

        without_token = client.get("/api/v1/portfolio")
        assert without_token.status_code == 401

        client.headers.update(
            {"Authorization": f"Bearer {payload['access_token']}"}
        )
        portfolios = client.get("/api/v1/portfolio")
        assert portfolios.status_code == 200
        assert portfolios.json() == []


def test_signup_rejects_duplicate_email_and_login_rejects_bad_password(tmp_path):
    with build_client(tmp_path) as client:
        payload = {
            "email": "duplicate@example.com",
            "password": "strong-password",
            "full_name": "Duplicate User",
        }
        assert client.post("/api/v1/auth/signup", json=payload).status_code == 201

        duplicate = client.post("/api/v1/auth/signup", json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"

        login = client.post(
            "/api/v1/auth/login",
            json={
                "email": "duplicate@example.com",
                "password": "wrong-password",
            },
        )
        assert login.status_code == 401
        assert login.json()["error"]["code"] == "INVALID_LOGIN"


def test_production_rejects_unsafe_auth_settings():
    try:
        Settings(
            environment="production",
            auth_secret_key="change-me-in-production",
            auth_cookie_secure=True,
        )
    except ValueError as exc:
        assert "AUTH_SECRET_KEY" in str(exc)
    else:
        raise AssertionError("production settings accepted the placeholder auth secret")


def test_production_rejects_documented_example_auth_secret():
    with pytest.raises(ValueError, match="AUTH_SECRET_KEY"):
        Settings(
            environment="production",
            auth_secret_key="replace-with-at-least-32-random-characters",
            auth_cookie_secure=True,
            database_ssl_mode="require",
        )


def test_production_requires_secure_auth_cookie():
    try:
        Settings(
            environment="production",
            auth_secret_key="a-production-secret-with-enough-length",
            auth_cookie_secure=False,
        )
    except ValueError as exc:
        assert "AUTH_COOKIE_SECURE" in str(exc)
    else:
        raise AssertionError("production settings accepted an insecure auth cookie")


def test_production_rejects_the_automated_test_market_provider():
    try:
        Settings(
            environment="production",
            auth_secret_key="a-production-secret-with-enough-length",
            auth_cookie_secure=True,
            market_data_provider="test-fixture",
        )
    except ValueError as exc:
        assert "MARKET_DATA_PROVIDER" in str(exc)
    else:
        raise AssertionError("production settings accepted the test market provider")


def test_login_rate_limit_is_durable_and_returns_retry_after(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'rate-limit.db'}",
        run_migrations_on_startup=True,
        auth_secret_key="test-secret",
        auth_login_rate_limit=2,
        auth_rate_limit_window_seconds=60,
    )
    with TestClient(create_app(settings)) as client:
        for _ in range(2):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "absent@example.com", "password": "wrong"},
            )
            assert response.status_code == 401

        limited = client.post(
            "/api/v1/auth/login",
            json={"email": "absent@example.com", "password": "wrong"},
        )
        assert limited.status_code == 429
        assert limited.json()["error"]["code"] == "RATE_LIMITED"
        assert int(limited.headers["retry-after"]) >= 1


def test_account_deletion_removes_owned_data_and_clears_cookie(tmp_path):
    with build_client(tmp_path) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "delete@example.com",
                "password": "strong-password",
                "full_name": "Delete User",
            },
        )
        assert signup.status_code == 201
        user_id = signup.json()["user"]["id"]

        portfolio = client.post(
            "/api/v1/portfolio",
            json={"name": "Delete me", "base_currency": "INR", "benchmark": "NIFTY50"},
        )
        assert portfolio.status_code == 201
        portfolio_id = portfolio.json()["id"]
        trade = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "RELIANCE.NS",
                "transaction_type": "BUY",
                "quantity": 1,
                "price": 100,
                "transaction_date": "2026-01-02",
            },
        )
        assert trade.status_code == 201

        deleted = client.request(
            "DELETE",
            "/api/v1/auth/account",
            json={"password": "strong-password", "confirmation": "DELETE"},
        )
        assert deleted.status_code == 204
        assert "rapra_access_token=\"\"" in deleted.headers["set-cookie"]

        db = client.app.state.session_factory()
        try:
            assert db.get(User, user_id) is None
            assert db.get(Portfolio, portfolio_id) is None
            assert db.query(Trade).count() == 0
        finally:
            db.close()


def test_production_requires_postgresql_and_database_tls():
    base = {
        "environment": "production",
        "auth_secret_key": "a-production-secret-with-enough-length",
        "auth_cookie_secure": True,
        "trusted_hosts": ["latent.example.com"],
        "cors_origins": ["https://latent.example.com"],
    }
    try:
        Settings(**base, database_url="sqlite:///./data/regime.db", database_ssl_mode="require")
    except ValueError as exc:
        assert "PostgreSQL" in str(exc)
    else:
        raise AssertionError("production settings accepted SQLite")

    try:
        Settings(
            **base,
            database_url="postgresql+psycopg://user:pass@db/latent",
            database_ssl_mode="disable",
        )
    except ValueError as exc:
        assert "TLS" in str(exc)
    else:
        raise AssertionError("production settings accepted a non-TLS database")

    try:
        Settings(
            **base,
            database_url="postgresql+psycopg://user:pass@db/latent",
            database_ssl_mode="require",
            regime_runtime_fit_enabled=False,
        )
    except ValueError as exc:
        assert "verify-full" in str(exc)
    else:
        raise AssertionError("production settings accepted TLS without identity verification")

    configured = Settings(
        **base,
        database_url="postgresql+psycopg://user:pass@db/latent",
        database_ssl_mode="verify-full",
        regime_runtime_fit_enabled=False,
    )
    assert configured.database_ssl_mode == "verify-full"
