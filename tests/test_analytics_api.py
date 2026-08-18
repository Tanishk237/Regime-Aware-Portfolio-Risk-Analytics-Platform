from pathlib import Path
import sys

import pandas as pd
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings
from src.database.models import MarketPrice, RegimePrediction, RiskMetric
from src.market.cache import market_data_cache
from src.market.providers import YahooFinanceProvider


def build_client(tmp_path, *, fii_dii_csv_path: str = "data/external/fii_dii.csv") -> TestClient:
    market_data_cache.clear()
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'analytics.db'}",
        run_migrations_on_startup=True,
        fii_dii_csv_path=fii_dii_csv_path,
        regime_model_dir=str(tmp_path / "models"),
    )
    return TestClient(create_app(settings))


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "analytics-test@example.com",
            "password": "strong-password",
            "full_name": "Analytics Test User",
        },
    )
    assert response.status_code == 201
    client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )


def create_portfolio_with_trades(client: TestClient) -> int:
    portfolio = client.post(
        "/api/v1/portfolio",
        json={
            "name": "Analytics Portfolio",
            "base_currency": "INR",
            "benchmark": "NIFTY50",
        },
    ).json()
    portfolio_id = portfolio["id"]
    for ticker, quantity, price in [
        ("RELIANCE.NS", 10, 100),
        ("INFY.NS", 5, 200),
    ]:
        response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": ticker,
                "transaction_type": "BUY",
                "quantity": quantity,
                "price": price,
                "transaction_date": "2024-01-01",
            },
        )
        assert response.status_code == 201
    return portfolio_id


def seed_market_prices(client: TestClient, days: int = 45) -> None:
    db = client.app.state.session_factory()
    try:
        dates = pd.date_range("2024-01-01", periods=days, freq="D")
        for index, row_date in enumerate(dates):
            for ticker, base in [("RELIANCE.NS", 100), ("INFY.NS", 200)]:
                close = base + index * (1.5 if ticker == "RELIANCE.NS" else 0.8)
                db.add(
                    MarketPrice(
                        ticker=ticker,
                        date=row_date.date(),
                        open=close - 0.5,
                        high=close + 1,
                        low=close - 1,
                        close=close,
                        volume=1000,
                    )
                )
        db.commit()
    finally:
        db.close()


def write_flow_csv(tmp_path, days: int = 45) -> str:
    dates = pd.date_range("2024-01-01", periods=days, freq="D")
    path = tmp_path / "flows.csv"
    path.write_text(
        "date,fii,dii\n"
        + "\n".join(
            f"{row_date.date()},{100 + index},{50 - index * 0.2}"
            for index, row_date in enumerate(dates)
        ),
        encoding="utf-8",
    )
    return str(path)


def test_risk_analytics_returns_metrics_series_pnl_and_persists(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio_with_trades(client)
        seed_market_prices(client)

        response = client.get(
            f"/api/v1/analytics/portfolio/{portfolio_id}/risk",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-02-14",
                "rolling_window": 5,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["portfolio_id"] == portfolio_id
        assert len(payload["returns"]) > 0
        assert payload["pnl"]["cost_basis"] == 2000
        assert payload["metrics"]["cagr"] is not None
        assert payload["metrics"]["historical_var"] <= payload["metrics"]["daily_mean_return"]
        assert "drawdown" in payload["series"]
        assert "rolling_volatility" in payload["series"]

        db = client.app.state.session_factory()
        try:
            assert db.query(RiskMetric).count() == 1
        finally:
            db.close()


def test_regime_analytics_returns_current_regime_history_and_persists(tmp_path, monkeypatch):
    flow_path = write_flow_csv(tmp_path)
    vix = pd.DataFrame(
        {"vix": [12 + index * 0.1 for index in range(45)]},
        index=pd.date_range("2024-01-01", periods=45, freq="D"),
    )
    monkeypatch.setattr(YahooFinanceProvider, "get_india_vix", lambda self, start_date, end_date: vix)

    with build_client(tmp_path, fii_dii_csv_path=flow_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio_with_trades(client)
        seed_market_prices(client)

        response = client.post(
            f"/api/v1/analytics/portfolio/{portfolio_id}/regime",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-02-14",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["portfolio_id"] == portfolio_id
        assert payload["current_regime"] in {"Bull", "Bear", "High Volatility"}
        assert 0 <= payload["regime_probability"] <= 1
        assert len(payload["regime_history"]) > 0
        assert len(payload["transition_matrix"]) == 3
        assert len(payload["regime_statistics"]) > 0
        assert len(payload["regime_duration"]) > 0
        assert payload["state_labels"]

        db = client.app.state.session_factory()
        try:
            assert db.query(RegimePrediction).count() == len(payload["regime_history"])
        finally:
            db.close()


def test_risk_analytics_rejects_invalid_date_range(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio_with_trades(client)

        response = client.get(
            f"/api/v1/analytics/portfolio/{portfolio_id}/risk",
            params={
                "start_date": "2024-02-01",
                "end_date": "2024-01-01",
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"
