from datetime import date
from pathlib import Path
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings
from src.database.models import FIIDIIHistory, MarketFeature, MarketPrice, VIXHistory
from src.market.cache import InMemoryMarketDataCache, market_data_cache
from src.market.market_service import MarketDataService
from src.market.providers import MarketDataProvider, YahooFinanceProvider


def build_client(tmp_path, *, fii_dii_csv_path: str = "data/external/fii_dii.csv") -> TestClient:
    market_data_cache.clear()
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'market.db'}",
        run_migrations_on_startup=True,
        fii_dii_csv_path=fii_dii_csv_path,
    )
    return TestClient(create_app(settings))


def test_historical_prices_are_normalized_and_persisted(tmp_path, monkeypatch):
    dates = pd.date_range("2024-01-01", periods=2, freq="D")
    columns = pd.MultiIndex.from_product(
        [["Open", "High", "Low", "Close", "Volume"],
         ["RELIANCE.NS", "INFY.NS"]]
    )
    raw_prices = pd.DataFrame(
        [
            [100, 200, 110, 210, 95, 190, 105, 205, 1000, 2000],
            [106, 206, 112, 216, 101, 202, 110, 212, 1100, 2100],
        ],
        index=dates,
        columns=columns,
    )

    monkeypatch.setattr(
        YahooFinanceProvider,
        "get_ohlcv",
        lambda self, tickers, start_date, end_date: raw_prices,
    )

    with build_client(tmp_path) as client:
        response = client.get(
            "/api/v1/market/historical-prices",
            params={
                "tickers": "reliance,infy.ns",
                "start_date": "2024-01-01",
                "end_date": "2024-01-03",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["tickers"] == ["INFY.NS", "RELIANCE.NS"]
        assert len(payload["prices"]) == 4
        reliance_prices = [
            price for price in payload["prices"] if price["ticker"] == "RELIANCE.NS"
        ]
        assert reliance_prices[0]["close"] == 105

        db = client.app.state.session_factory()
        try:
            assert db.query(MarketPrice).count() == 4
        finally:
            db.close()


def test_live_prices_return_frontend_ready_shape(tmp_path, monkeypatch):
    def fake_current_price(self, ticker, name=False):
        if name:
            return 2500.5, f"{ticker} Limited"
        return 2500.5

    monkeypatch.setattr(
        YahooFinanceProvider,
        "get_live_price",
        lambda self, ticker, include_name=False: {
            "ticker": ticker,
            "price": 2500.5,
            "name": f"{ticker} Limited" if include_name else None,
        },
    )

    with build_client(tmp_path) as client:
        response = client.get(
            "/api/v1/market/live-prices",
            params={"tickers": "reliance", "include_name": "true"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "prices": [
                {
                    "ticker": "RELIANCE.NS",
                    "price": 2500.5,
                    "name": "RELIANCE.NS Limited",
                }
            ],
        }


def test_india_vix_history_persists_snapshot(tmp_path, monkeypatch):
    vix = pd.DataFrame(
        {"vix": [12.0, 13.2, 12.8]},
        index=pd.date_range("2024-01-01", periods=3, freq="D"),
    )
    monkeypatch.setattr(YahooFinanceProvider, "get_india_vix", lambda self, start_date, end_date: vix)

    with build_client(tmp_path) as client:
        response = client.get(
            "/api/v1/market/india-vix",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-04",
                "window": 1,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert len(payload["points"]) == 3
        assert payload["points"][1]["vix_change"] == pytest.approx(0.1)

        db = client.app.state.session_factory()
        try:
            assert db.query(VIXHistory).count() == 3
        finally:
            db.close()


def test_fii_dii_flows_load_validate_and_persist(tmp_path):
    csv_path = tmp_path / "fii_dii.csv"
    csv_path.write_text(
        "date,fii,dii\n"
        "2024-01-01,100,50\n"
        "2024-01-02,-25,75\n",
        encoding="utf-8",
    )

    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'flows.db'}",
        run_migrations_on_startup=True,
    )
    with TestClient(create_app(settings)) as client:
        db = client.app.state.session_factory()
        try:
            records = MarketDataService(db, default_fii_dii_path=str(csv_path)).get_fii_dii_flows(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 2),
                window=1,
            )
            assert records[0]["net_flow"] == 150
            assert records[1]["net_flow_avg"] == 50
            assert db.query(FIIDIIHistory).count() == 2
        finally:
            db.close()


def test_feature_matrix_builds_validated_records_and_market_features(tmp_path, monkeypatch):
    dates = pd.date_range("2024-01-01", periods=45, freq="D")
    price_history = pd.DataFrame(
        {
            "RELIANCE.NS": [100 + index for index in range(45)],
            "INFY.NS": [200 + index * 0.5 for index in range(45)],
        },
        index=dates,
    )
    vix = pd.DataFrame(
        {"vix": [12 + index * 0.1 for index in range(45)]},
        index=dates,
    )
    flow_path = tmp_path / "flows.csv"
    flow_path.write_text(
        "date,fii,dii\n"
        + "\n".join(
            f"{day.date()},{100 + index},{50 - index * 0.2}"
            for index, day in enumerate(dates)
        ),
        encoding="utf-8",
    )

    def fake_ohlcv(self, tickers, start_date, end_date):
        ticker = tickers[0]
        close = price_history[ticker]
        return pd.DataFrame(
            {
                "Open": close,
                "High": close + 1,
                "Low": close - 1,
                "Close": close,
                "Volume": 1000,
            },
            index=price_history.index,
        )

    monkeypatch.setattr(YahooFinanceProvider, "get_ohlcv", fake_ohlcv)
    monkeypatch.setattr(YahooFinanceProvider, "get_india_vix", lambda self, start_date, end_date: vix)

    with build_client(tmp_path, fii_dii_csv_path=str(flow_path)) as client:
        response = client.post(
            "/api/v1/market/features/matrix",
            json={
                "tickers": ["reliance.ns", "infy.ns"],
                "start_date": "2024-01-01",
                "end_date": "2024-02-14",
                "weights": [0.6, 0.4],
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["validation"]["is_valid"] is True
        assert payload["metadata"]["n_samples"] == len(payload["records"])
        assert "portfolio_return" in payload["columns"]
        assert "vix" in payload["columns"]
        assert "net_flow" in payload["columns"]

        db = client.app.state.session_factory()
        try:
            assert db.query(MarketFeature).count() > 0
        finally:
            db.close()


def test_feature_matrix_rejects_weight_mismatch(tmp_path):
    with build_client(tmp_path) as client:
        response = client.post(
            "/api/v1/market/features/matrix",
            json={
                "tickers": ["RELIANCE.NS", "INFY.NS"],
                "start_date": "2024-01-01",
                "weights": [1.0],
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "WEIGHTS_TICKERS_MISMATCH"


def test_market_endpoints_reject_invalid_date_range(tmp_path):
    with build_client(tmp_path) as client:
        response = client.get(
            "/api/v1/market/fii-dii-flows",
            params={
                "start_date": "2024-02-01",
                "end_date": "2024-01-01",
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"


class CountingProvider(MarketDataProvider):
    name = "counting"

    def __init__(self):
        self.live_calls = 0

    def get_ohlcv(self, tickers, start_date, end_date=None):
        return pd.DataFrame()

    def get_live_price(self, ticker, include_name=False):
        self.live_calls += 1
        return {"ticker": ticker, "price": 100.0, "name": None}

    def get_india_vix(self, start_date, end_date=None):
        return pd.DataFrame()


class FailingProvider(MarketDataProvider):
    name = "failing"

    def get_ohlcv(self, tickers, start_date, end_date=None):
        raise RuntimeError("provider down")

    def get_live_price(self, ticker, include_name=False):
        raise RuntimeError("provider down")

    def get_india_vix(self, start_date, end_date=None):
        raise RuntimeError("provider down")


def test_live_prices_use_cache_before_provider(tmp_path):
    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        provider = CountingProvider()
        try:
            service = MarketDataService(
                db,
                provider=provider,
                cache=InMemoryMarketDataCache(),
                cache_ttl_seconds=900,
            )
            first = service.get_live_prices(["RELIANCE.NS"])
            second = service.get_live_prices(["RELIANCE.NS"])

            assert first == second
            assert provider.live_calls == 1
        finally:
            db.close()


def test_provider_failure_falls_back_to_stored_historical_prices(tmp_path):
    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        try:
            db.add(
                MarketPrice(
                    ticker="RELIANCE.NS",
                    date=date(2024, 1, 1),
                    open=100,
                    high=110,
                    low=95,
                    close=105,
                    volume=1000,
                )
            )
            db.commit()

            service = MarketDataService(
                db,
                provider=FailingProvider(),
                cache=InMemoryMarketDataCache(),
            )
            records = service.get_historical_prices(
                ["RELIANCE.NS"],
                date(2024, 1, 1),
                date(2024, 1, 2),
            )

            assert len(records) == 1
            assert records[0]["close"] == 105
        finally:
            db.close()


def test_invalid_provider_prices_are_rejected(tmp_path):
    class InvalidPriceProvider(CountingProvider):
        def get_ohlcv(self, tickers, start_date, end_date=None):
            return pd.DataFrame(
                {
                    "Open": [100],
                    "High": [90],
                    "Low": [95],
                    "Close": [-1],
                    "Volume": [1000],
                },
                index=pd.to_datetime(["2024-01-01"]),
            )

    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        try:
            service = MarketDataService(
                db,
                provider=InvalidPriceProvider(),
                cache=InMemoryMarketDataCache(),
            )
            with pytest.raises(Exception) as exc:
                service.get_historical_prices(
                    ["RELIANCE.NS"],
                    date(2024, 1, 1),
                    date(2024, 1, 1),
                )

            assert getattr(exc.value, "code", None) == "MARKET_DATA_VALIDATION_FAILED"
        finally:
            db.close()
