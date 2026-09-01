from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai import CopilotAIService
from src.api.main import create_app
from src.config.settings import Settings


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'ai.db'}",
        run_migrations_on_startup=True,
    )
    return TestClient(create_app(settings))


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "ai-test@example.com",
            "password": "strong-password",
            "full_name": "AI Test User",
        },
    )
    assert response.status_code == 201
    client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )


def test_copilot_chat_requires_auth(tmp_path):
    with build_client(tmp_path) as client:
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "provider": "openai",
                "api_key": "test-key-123",
                "prompt": "Explain my risk.",
                "context": {},
                "history": [],
            },
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_copilot_chat_calls_ai_service_for_authenticated_user(tmp_path, monkeypatch):
    captured = {}

    async def fake_generate(self, **kwargs):
        captured.update(kwargs)
        return {
            "provider": kwargs["provider"],
            "model": "test-model",
            "answer": "LLM generated answer",
            "fallback_used": False,
        }

    monkeypatch.setattr(CopilotAIService, "generate", fake_generate)

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "provider": "openai",
                "api_key": "test-key-123",
                "prompt": "Explain my risk.",
                "model": "custom-model",
                "context": {"summary": {"current_value": 1000}},
                "history": [{"role": "user", "content": "Earlier question"}],
            },
        )

        assert response.status_code == 200
        assert response.json()["answer"] == "LLM generated answer"
        assert captured["provider"] == "openai"
        assert captured["api_key"] == "test-key-123"
        assert captured["model"] == "custom-model"
        assert captured["context"]["summary"]["current_value"] == 1000
        assert captured["context"]["user"]["email"] == "ai-test@example.com"


def test_gemini_default_model_matches_google_ai_studio_api():
    assert CopilotAIService.DEFAULT_MODELS["gemini"] == "gemini-2.0-flash"


def test_gemini_model_resource_accepts_short_or_full_model_name():
    assert CopilotAIService._gemini_model_resource("gemini-2.0-flash") == "models/gemini-2.0-flash"
    assert CopilotAIService._gemini_model_resource("models/gemini-2.0-flash") == "models/gemini-2.0-flash"
