from datetime import date
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.analytics import AnalyticsService
from src.config.settings import Settings
from src.intelligence import PortfolioIntelligenceContextService, RiskProfileService
from src.intelligence.cache import PortfolioAnalyticsCache
from src.portfolio.portfolio_service import PortfolioService


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'intelligence.db'}",
        run_migrations_on_startup=True,
        auth_secret_key="intelligence-api-test-secret",
    )
    return TestClient(create_app(settings))


def signup_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "strong-password",
            "full_name": "Intelligence Test User",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_portfolio(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/portfolio",
        headers=headers,
        json={
            "name": "Intelligence Portfolio",
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
            "current_value": 100_000,
            "invested_value": 110_000,
            "total_return": -0.090909,
            "total_pnl": -10_000,
        },
        "positions": [
            {
                "ticker": "RELIANCE.NS",
                "quantity": 20,
                "avg_cost": 3_000,
                "cost_basis": 60_000,
                "current_price": 3_000,
                "market_value": 60_000,
                "market_weight": 0.60,
                "unrealized_pnl": 0,
                "realized_pnl": 0,
                "updated_at": None,
            },
            {
                "ticker": "INFY.NS",
                "quantity": 20,
                "avg_cost": 2_000,
                "cost_basis": 40_000,
                "current_price": 2_000,
                "market_value": 40_000,
                "market_weight": 0.40,
                "unrealized_pnl": 0,
                "realized_pnl": 0,
                "updated_at": None,
            },
        ],
        "risk": {
            "metrics": {
                "max_drawdown": -0.28,
                "annualized_volatility": 0.29,
                "historical_var": -0.025,
                "historical_cvar": -0.041,
                "sharpe": 0.2,
                "sortino": 0.25,
            }
        },
        "regime": {
            "current_regime": "Bear",
            "regime_probability": 0.84,
        },
        "risk_profile": profile,
        "executive_summary": [
            "The portfolio is down 9.09% on invested capital.",
            "The current market state is Bear at 84.0% state-fit probability.",
        ],
        "citations": [
            {
                "label": "Total return",
                "value": "-0.090909",
                "source": "portfolio_summary",
                "as_of": date(2026, 9, 15),
            }
        ],
        "warnings": [],
    }


def test_intelligence_workspace_is_grounded_and_actionable(tmp_path, monkeypatch):
    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)

    with build_client(tmp_path) as client:
        headers = signup_headers(client, "owner@example.com")
        portfolio_id = create_portfolio(client, headers)

        response = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}", headers=headers
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["total_return"] == -0.090909
        assert payload["risk"]["metrics"]["max_drawdown"] == -0.28
        assert payload["regime"]["current_regime"] == "Bear"
        assert payload["recommendations"]
        assert payload["alerts"]
        assert all(item["evidence"] for item in payload["recommendations"])
        assert all(item["action"] for item in payload["recommendations"])
        assert "negative-total-return" in {
            item["fingerprint"] for item in payload["recommendations"]
        }
        assert {item["category"] for item in payload["recommendations"]} >= {
            "Risk",
            "Diversification",
            "Regime",
            "Performance",
        }

        explanation = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}/explanations/max_drawdown",
            headers=headers,
        )
        assert explanation.status_code == 200
        assert explanation.json()["value"] == "-28.00%"
        assert "exceeds" in explanation.json()["interpretation"]

        for metric in (
            "period_return",
            "calmar",
            "parametric_var",
            "parametric_cvar",
            "daily_mean_return",
        ):
            response = client.get(
                f"/api/v1/intelligence/portfolio/{portfolio_id}/explanations/{metric}",
                headers=headers,
            )
            assert response.status_code == 200
            assert response.json()["source"] == "risk_analytics"

        recommendation = payload["recommendations"][0]
        read = client.patch(
            f"/api/v1/intelligence/portfolio/{portfolio_id}/recommendations/{recommendation['id']}",
            headers=headers,
            json={"is_read": True},
        )
        assert read.status_code == 200
        assert read.json()["is_read"] is True


def test_stress_prompt_requires_confirmation_and_persists_result(tmp_path, monkeypatch):
    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)

    with build_client(tmp_path) as client:
        headers = signup_headers(client, "stress@example.com")
        portfolio_id = create_portfolio(client, headers)
        preview = client.post(
            f"/api/v1/intelligence/portfolio/{portfolio_id}/stress/parse",
            headers=headers,
            json={
                "prompt": "Market falls 12%, RELIANCE falls 20%, and VIX rises 30%."
            },
        )
        assert preview.status_code == 200
        scenario = preview.json()
        assert scenario["market_shock"] == -12
        assert scenario["ticker_shocks"]["RELIANCE.NS"] == -20
        assert scenario["volatility_shock"] == 30

        unconfirmed = client.post(
            f"/api/v1/intelligence/portfolio/{portfolio_id}/stress/run",
            headers=headers,
            json={
                "name": scenario["name"],
                "market_shock": scenario["market_shock"],
                "volatility_shock": scenario["volatility_shock"],
                "ticker_shocks": scenario["ticker_shocks"],
                "confirmed": False,
            },
        )
        assert unconfirmed.status_code == 409
        assert unconfirmed.json()["error"]["code"] == "STRESS_CONFIRMATION_REQUIRED"

        completed = client.post(
            f"/api/v1/intelligence/portfolio/{portfolio_id}/stress/run",
            headers=headers,
            json={
                "name": scenario["name"],
                "market_shock": scenario["market_shock"],
                "volatility_shock": scenario["volatility_shock"],
                "ticker_shocks": scenario["ticker_shocks"],
                "confirmed": True,
            },
        )
        assert completed.status_code == 200
        assert completed.json()["value_after"] == 83_200
        assert round(completed.json()["estimated_impact_pct"], 3) == -0.168


def test_profile_and_intelligence_are_user_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(PortfolioIntelligenceContextService, "build", fake_context)

    with build_client(tmp_path) as client:
        owner = signup_headers(client, "profile-owner@example.com")
        intruder = signup_headers(client, "profile-intruder@example.com")
        portfolio_id = create_portfolio(client, owner)

        updated = client.put(
            "/api/v1/intelligence/profile",
            headers=owner,
            json={
                "tolerance": "conservative",
                "horizon_months": 36,
                "max_drawdown_tolerance": 0.12,
                "liquidity_needs": "high",
                "income_requirement": "Quarterly income",
                "restrictions": ["No leveraged products"],
            },
        )
        assert updated.status_code == 200
        assert updated.json()["tolerance"] == "conservative"

        hidden = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}", headers=intruder
        )
        assert hidden.status_code == 404
        assert hidden.json()["error"]["code"] == "PORTFOLIO_NOT_FOUND"


def test_intelligence_reuses_recent_analytics_and_explicit_refresh_bypasses_cache(
    tmp_path,
    monkeypatch,
):
    calls = {"risk": 0, "regime": 0}

    def risk_payload(self, user, portfolio_id, **kwargs):
        calls["risk"] += 1
        return {
            "portfolio_id": portfolio_id,
            "as_of": date(2026, 9, 15),
            "returns": [],
            "pnl": {},
            "metrics": {},
            "series": {},
        }

    def regime_payload(self, user, portfolio_id, **kwargs):
        calls["regime"] += 1
        return {
            "portfolio_id": portfolio_id,
            "current_regime": "Neutral",
            "regime_probability": 0.60,
        }

    monkeypatch.setattr(AnalyticsService, "build_risk_payload", risk_payload)
    monkeypatch.setattr(AnalyticsService, "build_regime_payload", regime_payload)

    with build_client(tmp_path) as client:
        headers = signup_headers(client, "cache-owner@example.com")
        portfolio_id = create_portfolio(client, headers)

        first = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}",
            headers=headers,
        )
        second = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}",
            headers=headers,
        )
        updated = client.put(
            f"/api/v1/portfolio/{portfolio_id}",
            headers=headers,
            json={"name": "Updated cache portfolio"},
        )
        after_mutation = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}",
            headers=headers,
        )
        refreshed = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}",
            params={"refresh": "true"},
            headers=headers,
        )

        assert updated.status_code == 200
        assert (
            first.status_code
            == second.status_code
            == after_mutation.status_code
            == refreshed.status_code
            == 200
        )
        assert calls == {"risk": 3, "regime": 3}


def test_alert_list_is_a_lightweight_persisted_read(tmp_path, monkeypatch):
    def fail_if_context_is_built(*args, **kwargs):
        raise AssertionError("alert reads must not rebuild portfolio analytics")

    monkeypatch.setattr(
        PortfolioIntelligenceContextService,
        "build",
        fail_if_context_is_built,
    )

    with build_client(tmp_path) as client:
        headers = signup_headers(client, "alert-reader@example.com")
        portfolio_id = create_portfolio(client, headers)
        response = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}/alerts",
            headers=headers,
        )

        assert response.status_code == 200
        assert response.json() == []


def test_portfolio_analytics_cache_is_revision_aware_and_returns_copies():
    cache = PortfolioAnalyticsCache(max_entries=1)
    cache.set("db", 1, "revision-1", {"risk": {"value": 10}}, 60)

    first = cache.get("db", 1, "revision-1")
    assert first == {"risk": {"value": 10}}
    first["risk"]["value"] = 99
    assert cache.get("db", 1, "revision-1") == {"risk": {"value": 10}}
    assert cache.get("db", 1, "revision-2") is None


def test_sector_allocation_uses_current_value_and_normalizes_weights():
    allocation = PortfolioIntelligenceContextService._sector_allocation(
        [
            {
                "ticker": "INFY.NS",
                "quantity": 10,
                "market_value": 40_000,
                "cost_basis": 35_000,
                "sector": "Technology",
            },
            {
                "ticker": "TCS.NS",
                "quantity": 5,
                "market_value": 20_000,
                "cost_basis": 25_000,
                "sector": "Technology",
            },
            {
                "ticker": "HDFCBANK.NS",
                "quantity": 10,
                "market_value": 40_000,
                "cost_basis": 30_000,
                "sector": "Financial Services",
            },
        ]
    )

    assert [item["sector"] for item in allocation] == [
        "Technology",
        "Financial Services",
    ]
    assert allocation[0]["market_value"] == 60_000
    assert allocation[0]["weight"] == pytest.approx(0.60)
    assert allocation[0]["holdings_count"] == 2
    assert sum(item["weight"] for item in allocation) == pytest.approx(1.0)
