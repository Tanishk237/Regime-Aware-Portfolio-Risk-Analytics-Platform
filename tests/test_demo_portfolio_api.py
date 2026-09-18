from datetime import date, timedelta
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings
from src.api.errors import AppError
from src.database.models import AIReport, PortfolioAlert, RiskProfile
from src.market import MarketDataService
from src.market.cache import InMemoryMarketDataCache
from src.market.providers import MarketDataProvider


class FailingProvider(MarketDataProvider):
    name = "failing"

    def get_ohlcv(self, tickers, start_date, end_date=None):
        raise RuntimeError("provider unavailable")

    def get_live_price(self, ticker, *, include_name=False):
        raise RuntimeError("provider unavailable")

    def get_india_vix(self, start_date, end_date=None):
        raise RuntimeError("provider unavailable")


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'demo.db'}",
        run_migrations_on_startup=True,
        auth_secret_key="demo-portfolio-test-secret",
    )
    return TestClient(create_app(settings))


def guest_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/auth/guest")
    assert response.status_code == 201
    payload = response.json()
    assert payload["user"]["is_guest"] is True
    return {"Authorization": f"Bearer {payload['access_token']}"}


def test_guest_can_create_and_reset_an_isolated_demo_portfolio(tmp_path):
    with build_client(tmp_path) as client:
        owner = guest_headers(client)
        other_guest = guest_headers(client)

        created = client.post("/api/v1/portfolio/demo", headers=owner)
        assert created.status_code == 201
        payload = created.json()
        portfolio = payload["portfolio"]
        assert portfolio["is_demo"] is True
        assert payload["trades_created"] == 6

        positions = client.get(f"/api/v1/portfolio/{portfolio['id']}/positions", headers=owner)
        assert positions.status_code == 200
        assert len(positions.json()) == 6

        summary = client.get(f"/api/v1/portfolio/{portfolio['id']}/summary", headers=owner)
        assert summary.status_code == 200
        assert summary.json()["current_value"] is not None

        hidden_from_other_guest = client.get(
            f"/api/v1/portfolio/{portfolio['id']}",
            headers=other_guest,
        )
        assert hidden_from_other_guest.status_code == 404

        repeated = client.post("/api/v1/portfolio/demo", headers=owner)
        assert repeated.status_code == 201
        assert repeated.json()["portfolio"]["id"] == portfolio["id"]
        assert repeated.json()["trades_created"] == 0

        extra_trade = client.post(
            f"/api/v1/portfolio/{portfolio['id']}/trades",
            headers=owner,
            json={
                "ticker": "ITC.NS",
                "transaction_type": "BUY",
                "quantity": 20,
                "price": 420,
                "transaction_date": "2026-01-01",
            },
        )
        assert extra_trade.status_code == 201

        reset = client.post("/api/v1/portfolio/demo/reset", headers=owner)
        assert reset.status_code == 200
        assert reset.json()["trades_created"] == 6
        reset_id = reset.json()["portfolio"]["id"]
        reset_trades = client.get(f"/api/v1/portfolio/{reset_id}/trades", headers=owner)
        assert reset_trades.status_code == 200
        assert len(reset_trades.json()) == 6
        assert all(row["ticker"] != "ITC.NS" for row in reset_trades.json())


def test_ending_a_guest_session_removes_access_to_its_workspace(tmp_path):
    with build_client(tmp_path) as client:
        headers = guest_headers(client)
        created = client.post("/api/v1/portfolio/demo", headers=headers)
        assert created.status_code == 201
        portfolio_id = created.json()["portfolio"]["id"]
        user_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]

        profile = client.get("/api/v1/intelligence/profile", headers=headers)
        assert profile.status_code == 200
        intelligence = client.get(
            f"/api/v1/intelligence/portfolio/{portfolio_id}", headers=headers
        )
        assert intelligence.status_code == 200
        report = client.post(
            "/api/v1/ai/reports",
            headers=headers,
            json={
                "portfolio_id": portfolio_id,
                "report_type": "Portfolio Summary",
                "provider": "openai",
            },
        )
        assert report.status_code == 200

        ended = client.delete("/api/v1/auth/guest-session", headers=headers)
        assert ended.status_code == 204

        after_end = client.get("/api/v1/portfolio", headers=headers)
        assert after_end.status_code == 401

        db = client.app.state.session_factory()
        try:
            assert db.query(RiskProfile).filter_by(user_id=user_id).count() == 0
            assert db.query(AIReport).filter_by(user_id=user_id).count() == 0
            assert db.query(PortfolioAlert).filter_by(portfolio_id=portfolio_id).count() == 0
        finally:
            db.close()


def test_demo_market_history_is_not_a_real_user_market_data_fallback(tmp_path):
    with build_client(tmp_path) as client:
        headers = guest_headers(client)
        created = client.post("/api/v1/portfolio/demo", headers=headers)
        assert created.status_code == 201

        db = client.app.state.session_factory()
        try:
            start_date = date.today() - timedelta(days=365)
            service = MarketDataService(
                db,
                provider=FailingProvider(),
                cache=InMemoryMarketDataCache(),
            )
            with pytest.raises(AppError) as exc:
                service.get_historical_prices(
                    ["RELIANCE.NS"],
                    start_date=start_date,
                )
            assert exc.value.code == "MARKET_DATA_UNAVAILABLE"

            demo_service = MarketDataService(
                db,
                provider=FailingProvider(),
                cache=InMemoryMarketDataCache(),
                allow_demo_data=True,
            )
            assert demo_service.get_historical_prices(
                ["RELIANCE.NS"],
                start_date=start_date,
            )
        finally:
            db.close()
