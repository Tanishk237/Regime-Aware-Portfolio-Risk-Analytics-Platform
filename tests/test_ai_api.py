from datetime import date
import asyncio
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai import CopilotAIService
from src.ai.retrieval import LocalContextRetriever, REGIME_MODEL_DISCLOSURE
from src.api.errors import AppError
from src.api.main import create_app
from src.config.settings import Settings
from src.intelligence import PortfolioIntelligenceContextService, RiskProfileService
from src.portfolio.portfolio_service import PortfolioService


def build_client(tmp_path, **overrides) -> TestClient:
    values = {
        "environment": "test",
        "database_url": f"sqlite:///{tmp_path / 'ai.db'}",
        "run_migrations_on_startup": True,
        "auth_secret_key": "ai-api-test-secret",
    }
    values.update(overrides)
    settings = Settings(
        **values,
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


def create_portfolio(client: TestClient) -> int:
    response = client.post(
        "/api/v1/portfolio",
        json={
            "name": "AI Portfolio",
            "base_currency": "INR",
            "benchmark": "NIFTY50",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def fake_context(self, user, portfolio_id):
    portfolio = PortfolioService(self.db).get_portfolio(user, portfolio_id)
    profile = RiskProfileService(self.db).get_or_create(user)
    return {
        "portfolio_id": portfolio.id,
        "data_as_of": date(2026, 9, 15),
        "summary": {
            "name": portfolio.name,
            "base_currency": portfolio.base_currency,
            "current_value": 110_000,
            "invested_value": 100_000,
            "total_return": 0.10,
            "total_pnl": 10_000,
        },
        "positions": [],
        "risk": {"metrics": {"max_drawdown": -0.08}},
        "regime": {"current_regime": "Bull", "regime_probability": 0.82},
        "risk_profile": profile,
        "executive_summary": ["The portfolio is up 10.00% on invested capital."],
        "citations": [
            {
                "label": "Total return",
                "value": "0.1",
                "source": "portfolio_summary",
                "as_of": date(2026, 9, 15),
            }
        ],
        "warnings": [],
    }


def test_copilot_chat_requires_auth(tmp_path):
    with build_client(tmp_path) as client:
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "portfolio_id": 1,
                "provider": "openai",
                "prompt": "Explain my risk.",
            },
        )

        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_copilot_uses_server_context_for_authenticated_user(tmp_path, monkeypatch):
    captured = {}

    async def fake_generate(self, **kwargs):
        captured.update(kwargs)
        return {
            "provider": kwargs["provider"],
            "model": "test-model",
            "answer": "LLM generated answer",
            "fallback_used": False,
        }

    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)
    monkeypatch.setattr(CopilotAIService, "generate", fake_generate)

    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio(client)
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "portfolio_id": portfolio_id,
                "provider": "openai",
                "api_key": "test-key-123",
                "prompt": "Explain my risk.",
                "model": "custom-model",
                "history": [{"role": "user", "content": "Earlier question"}],
            },
        )

        assert response.status_code == 200
        assert response.json()["answer"] == "LLM generated answer"
        assert response.json()["response_mode"] == "provider"
        assert response.json()["tools_used"] == [
            "get_portfolio_summary",
            "get_risk_metrics",
        ]
        assert captured["provider"] == "openai"
        assert captured["api_key"] == "test-key-123"
        assert captured["model"] == "custom-model"
        assert captured["context"]["tool_results"]["portfolio_summary"][
            "current_value"
        ] == 110_000
        assert "user" not in captured["context"]


def test_copilot_without_key_is_transparently_local(tmp_path, monkeypatch):
    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)

    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio(client)
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "portfolio_id": portfolio_id,
                "provider": "gemini",
                "prompt": "Explain my regime.",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["response_mode"] == "local"
        assert payload["fallback_used"] is True
        assert "Portfolio Snapshot" in payload["answer"]
        assert REGIME_MODEL_DISCLOSURE in payload["answer"]
        assert payload["data_as_of"] == "2026-09-15"


def test_nvidia_uses_only_server_managed_key(tmp_path, monkeypatch):
    captured = {}

    async def fake_generate(self, **kwargs):
        captured.update(kwargs)
        return {
            "provider": "nvidia",
            "model": kwargs["model"],
            "answer": "Server-managed response",
            "fallback_used": False,
            "retrieval": None,
        }

    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)
    monkeypatch.setattr(CopilotAIService, "generate", fake_generate)

    with build_client(tmp_path, nvidia_api_key="server-only-key") as client:
        authenticate(client)
        portfolio_id = create_portfolio(client)
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "portfolio_id": portfolio_id,
                "provider": "nvidia",
                "api_key": "untrusted-browser-key",
                "prompt": "Explain the regime.",
            },
        )

        assert response.status_code == 200
        assert response.json()["response_mode"] == "provider"
        assert captured["api_key"] == "server-only-key"
        assert "server-only-key" not in response.text
        assert "untrusted-browser-key" not in response.text


def test_copilot_defaults_to_server_managed_nvidia(tmp_path, monkeypatch):
    captured = {}

    async def fake_generate(self, **kwargs):
        captured.update(kwargs)
        return {
            "provider": kwargs["provider"],
            "model": kwargs["model"],
            "answer": "Managed default response",
            "fallback_used": False,
            "retrieval": None,
        }

    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)
    monkeypatch.setattr(CopilotAIService, "generate", fake_generate)

    with build_client(tmp_path, nvidia_api_key="server-only-key") as client:
        authenticate(client)
        portfolio_id = create_portfolio(client)
        response = client.post(
            "/api/v1/ai/copilot/chat",
            json={
                "portfolio_id": portfolio_id,
                "api_key": "browser-key-must-be-ignored",
                "model": "browser-model-must-be-ignored",
                "prompt": "Explain my risk.",
            },
        )

        assert response.status_code == 200
        assert response.json()["provider"] == "nvidia"
        assert (
            response.json()["model"]
            == "nvidia/nemotron-3.5-lightning-30b-a3b"
        )
        assert captured["api_key"] == "server-only-key"
        assert captured["model"] == "nvidia/nemotron-3.5-lightning-30b-a3b"
        assert "server-only-key" not in response.text
        assert "browser-key-must-be-ignored" not in response.text


def test_provider_config_exposes_readiness_without_secret(tmp_path):
    with build_client(tmp_path, nvidia_api_key="server-only-key") as client:
        authenticate(client)
        response = client.get("/api/v1/ai/provider/config")

        assert response.status_code == 200
        payload = response.json()
        assert payload == {
            "default_provider": "nvidia",
            "managed_provider": "nvidia",
            "managed_provider_configured": True,
            "managed_model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }
        assert "server-only-key" not in response.text


def test_nvidia_retries_a_compatible_server_model(tmp_path, monkeypatch):
    attempted_models = []

    async def fake_generate(self, **kwargs):
        attempted_models.append(kwargs["model"])
        if len(attempted_models) == 1:
            raise AppError(
                "The selected AI provider rejected the request.",
                code="AI_PROVIDER_ERROR",
                status_code=502,
                details={"provider": "nvidia", "status_code": 404},
            )
        return {
            "provider": "nvidia",
            "model": kwargs["model"],
            "answer": "connected",
            "fallback_used": False,
            "retrieval": None,
        }

    monkeypatch.setattr(CopilotAIService, "generate", fake_generate)

    with build_client(tmp_path, nvidia_api_key="server-only-key") as client:
        authenticate(client)
        response = client.post(
            "/api/v1/ai/provider/validate",
            json={"provider": "nvidia"},
        )

        assert response.status_code == 200
        assert response.json()["model"] == "z-ai/glm-5.3-flash"
        assert attempted_models == [
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "z-ai/glm-5.3-flash",
        ]


def test_local_retrieval_is_compact_and_uses_no_embedding_api_tokens():
    retriever = LocalContextRetriever(top_k=3, character_budget=1600)
    result = retriever.retrieve(
        "What are my largest risk and drawdown drivers?",
        {
            "data_as_of": "2026-09-15",
            "tool_results": {
                "portfolio_summary": {"current_value": 110_000},
                "risk_metrics": {
                    "max_drawdown": -0.08,
                    "series": [{"date": index, "value": index} for index in range(500)],
                },
                "regime_analytics": {"current_regime": "Bull"},
            },
        },
    )

    metadata = result.metadata()
    assert result.selected_sources[0] == "model_disclosure"
    assert "risk_metrics" in result.selected_sources
    assert REGIME_MODEL_DISCLOSURE in result.context
    assert result.context_characters <= 1600
    assert metadata["external_embedding_tokens"] == 0
    assert metadata["selected_documents"] <= 3


def test_langchain_provider_receives_retrieved_context(monkeypatch):
    captured = {}

    async def fake_openai_compatible(self, **kwargs):
        captured.update(kwargs)
        return "Grounded answer"

    monkeypatch.setattr(CopilotAIService, "_openai_compatible", fake_openai_compatible)
    result = asyncio.run(
        CopilotAIService(retrieval_top_k=2, retrieval_character_budget=1400).generate(
            provider="nvidia",
            api_key="server-only-key",
            prompt="Explain regime confidence.",
            context={"tool_results": {"regime_analytics": {"regime_probability": 1.0}}},
            model="nvidia/nemotron-3.5-lightning-30b-a3b",
        )
    )

    assert result["answer"] == "Grounded answer"
    assert result["retrieval"]["strategy"] == "local_hash_embeddings"
    assert result["retrieval"]["external_embedding_tokens"] == 0
    assert REGIME_MODEL_DISCLOSURE in captured["system_prompt"]
    assert captured["extra_body"] == {
        "chat_template_kwargs": {"enable_thinking": False}
    }


def test_report_generation_persists_response_mode(tmp_path, monkeypatch):
    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)

    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio(client)
        generated = client.post(
            "/api/v1/ai/reports",
            json={
                "portfolio_id": portfolio_id,
                "report_type": "Portfolio Summary",
                "provider": "openai",
            },
        )
        assert generated.status_code == 200
        assert generated.json()["response_mode"] == "local"
        assert "Executive summary" in generated.json()["content"]
        assert "Current value: INR 110,000.00" in generated.json()["content"]
        assert "Invested capital: INR 100,000.00" in generated.json()["content"]

        history = client.get(f"/api/v1/ai/reports/{portfolio_id}")
        assert history.status_code == 200
        assert history.json()[0]["response_mode"] == "local"
        assert history.json()[0]["id"] == generated.json()["id"]


def test_byok_defaults_use_active_provider_models():
    assert CopilotAIService.DEFAULT_MODELS["gemini"] == "gemini-flash-latest"
    assert (
        CopilotAIService.DEFAULT_MODELS["claude"]
        == "claude-haiku-4-5-20251001"
    )


def test_nvidia_default_model_matches_api_catalog_slug():
    assert (
        CopilotAIService.DEFAULT_MODELS["nvidia"]
        == "nvidia/nemotron-3.5-lightning-30b-a3b"
    )


def test_gemini_model_resource_accepts_short_or_full_model_name():
    assert (
        CopilotAIService._gemini_model_resource("gemini-2.0-flash")
        == "models/gemini-2.0-flash"
    )
    assert (
        CopilotAIService._gemini_model_resource("models/gemini-2.0-flash")
        == "models/gemini-2.0-flash"
    )
