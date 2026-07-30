import sys
from pathlib import Path

from fastapi import APIRouter
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.errors import AppError
from src.api.main import create_app
from src.config.settings import Settings


def build_client() -> TestClient:
    settings = Settings(
        app_name="Regime Test API",
        app_version="9.9.9",
        environment="test",
        api_prefix="/api/v1",
        cors_origins=["http://localhost:3000"],
    )

    return TestClient(
        create_app(settings)
    )


def test_health_endpoint():
    client = build_client()

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "ok"
    assert payload["service"] == "Regime Test API"
    assert payload["environment"] == "test"
    assert "timestamp" in payload


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
