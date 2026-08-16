from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings


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
        assert me.status_code == 200
        assert me.json()["email"] == "user@example.com"

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
