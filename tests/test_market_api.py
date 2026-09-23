from datetime import date
from pathlib import Path
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.api.dependencies import get_current_user
from src.api.errors import AppError
from src.config.settings import Settings
from src.database.models import (
    FIIDIIHistory,
    InstrumentMetadata,
    MarketFeature,
    MarketPrice,
    VIXHistory,
    User,
)
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
    app = create_app(settings)
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="market-test@example.com",
        full_name="Market Test",
        password_hash="test",
        is_active=True,
    )
    return TestClient(app)


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
                    "source": "yahoo",
                    "as_of": date.today().isoformat(),
                    "is_stale": False,
                }
            ],
        }


def test_public_live_prices_reject_oversized_ticker_requests(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'ticker-limit.db'}",
        run_migrations_on_startup=True,
        market_data_max_tickers_per_request=2,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/api/v1/market/live-prices",
            params={"tickers": "RELIANCE.NS,INFY.NS,TCS.NS"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TOO_MANY_TICKERS"


def test_historical_market_data_requires_authentication(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'market-auth.db'}",
        run_migrations_on_startup=True,
    )

    with TestClient(create_app(settings)) as client:
        response = client.get(
            "/api/v1/market/historical-prices",
            params={
                "tickers": "RELIANCE.NS",
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_live_price_fallback_identifies_stored_stale_data(tmp_path):
    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        try:
            db.add(
                MarketPrice(
                    ticker="RELIANCE.NS",
                    date=date(2024, 1, 1),
                    close=105,
                    data_source="provider",
                )
            )
            db.commit()
            records = MarketDataService(
                db,
                provider=FailingProvider(),
                cache=InMemoryMarketDataCache(),
            ).get_live_prices(["RELIANCE.NS"])

            assert records == [
                {
                    "ticker": "RELIANCE.NS",
                    "price": 105,
                    "name": None,
                    "source": "stored:provider",
                    "as_of": date(2024, 1, 1),
                    "is_stale": True,
                }
            ]
        finally:
            db.close()


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


def test_stored_vix_coverage_accepts_timestamp_dates(tmp_path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'vix.db'}",
        run_migrations_on_startup=True,
    )
    with TestClient(create_app(settings)) as client:
        db = client.app.state.session_factory()
        try:
            service = MarketDataService(db)
            assert service._stored_vix_covers_request(
                [
                    {"date": pd.Timestamp("2024-01-01"), "vix": 12.0},
                    {"date": pd.Timestamp("2024-01-05"), "vix": 13.0},
                ],
                date(2024, 1, 1),
                date(2024, 1, 5),
            )
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
        self.metadata_calls = 0

    def get_ohlcv(self, tickers, start_date, end_date=None):
        return pd.DataFrame()

    def get_live_price(self, ticker, include_name=False):
        self.live_calls += 1
        return {"ticker": ticker, "price": 100.0, "name": None}

    def get_india_vix(self, start_date, end_date=None):
        return pd.DataFrame()

    def get_instrument_metadata(self, ticker):
        self.metadata_calls += 1
        return {
            "ticker": ticker,
            "name": "Reliance Industries",
            "sector": "Energy",
            "industry": "Oil & Gas Integrated",
            "exchange": "NSE",
            "country": "India",
            "currency": "INR",
            "data_source": self.name,
        }


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


def test_instrument_metadata_is_persisted_and_cached(tmp_path):
    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        provider = CountingProvider()
        try:
            service = MarketDataService(
                db,
                provider=provider,
                cache=InMemoryMarketDataCache(),
            )
            first = service.get_instrument_metadata(["RELIANCE.NS"])
            second = service.get_instrument_metadata(["RELIANCE.NS"])

            assert first[0]["sector"] == "Energy"
            assert second[0]["sector"] == "Energy"
            assert provider.metadata_calls == 1
            stored = db.query(InstrumentMetadata).one()
            assert stored.ticker == "RELIANCE.NS"
            assert stored.data_source == "counting"
        finally:
            db.close()


def test_instrument_metadata_failure_returns_cached_other_value(tmp_path):
    class MetadataFailingProvider(CountingProvider):
        def get_instrument_metadata(self, ticker):
            self.metadata_calls += 1
            raise RuntimeError("metadata provider down")

    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        provider = MetadataFailingProvider()
        try:
            service = MarketDataService(
                db,
                provider=provider,
                cache=InMemoryMarketDataCache(),
            )
            first = service.get_instrument_metadata(["UNKNOWN.NS"])
            second = service.get_instrument_metadata(["UNKNOWN.NS"])

            assert first == second
            assert first[0]["sector"] == "Other"
            assert provider.metadata_calls == 1
        finally:
            db.close()


def test_market_cache_is_bounded_and_evicts_oldest_entry():
    cache = InMemoryMarketDataCache(max_entries=2)
    cache.set("first", {"price": 1}, 900)
    cache.set("second", {"price": 2}, 900)
    cache.set("third", {"price": 3}, 900)

    assert cache.get("first") is None
    assert cache.get("second") == {"price": 2}
    assert cache.get("third") == {"price": 3}


def test_provider_failure_rejects_incomplete_stored_historical_prices(tmp_path):
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
            with pytest.raises(AppError) as exc_info:
                service.get_historical_prices(
                    ["RELIANCE.NS"],
                    date(2024, 1, 1),
                    date(2024, 1, 2),
                )

            assert exc_info.value.code == "MARKET_DATA_INCOMPLETE"
            assert exc_info.value.status_code == 503
        finally:
            db.close()


def test_historical_prices_return_provider_records_without_persisting(tmp_path):
    class HistoricalProvider(CountingProvider):
        def get_ohlcv(self, tickers, start_date, end_date=None):
            close = pd.Series(
                [100.0, 101.0],
                index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
            )
            return pd.DataFrame(
                {
                    "Open": close,
                    "High": close + 1,
                    "Low": close - 1,
                    "Close": close,
                    "Volume": 1000,
                },
                index=close.index,
            )

    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        try:
            service = MarketDataService(
                db,
                provider=HistoricalProvider(),
                cache=InMemoryMarketDataCache(),
            )
            records = service.get_historical_prices(
                ["RELIANCE.NS"],
                date(2024, 1, 1),
                date(2024, 1, 2),
                persist=False,
            )

            assert len(records) == 2
            assert records[-1]["close"] == 101
            assert records[-1]["source"] == "counting"
            assert db.query(MarketPrice).count() == 0
            assert service.fetch_metadata["historical"]["coverage_complete"] is True
        finally:
            db.close()


def test_historical_prices_backfill_requested_range_when_only_latest_is_stored(tmp_path):
    class BackfillProvider(CountingProvider):
        def __init__(self):
            super().__init__()
            self.requests = []

        def get_ohlcv(self, tickers, start_date, end_date=None):
            self.requests.append((tickers, start_date, end_date))
            close = pd.Series(
                [100.0, 101.0, 102.0],
                index=pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            )
            return pd.DataFrame(
                {
                    "Open": close,
                    "High": close + 1,
                    "Low": close - 1,
                    "Close": close,
                    "Volume": 1000,
                },
                index=close.index,
            )

    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        provider = BackfillProvider()
        try:
            db.add(
                MarketPrice(
                    ticker="RELIANCE.NS",
                    date=date(2024, 1, 3),
                    open=102,
                    high=103,
                    low=101,
                    close=102,
                    volume=1000,
                )
            )
            db.commit()

            service = MarketDataService(
                db,
                provider=provider,
                cache=InMemoryMarketDataCache(),
            )
            records = service.get_historical_prices(
                ["RELIANCE.NS"],
                date(2024, 1, 1),
                date(2024, 1, 3),
            )

            assert provider.requests == [
                (["RELIANCE.NS"], date(2024, 1, 1), date(2024, 1, 2))
            ]
            assert len(records) == 3
            assert {record["date"] for record in records} == {
                date(2024, 1, 1),
                date(2024, 1, 2),
                date(2024, 1, 3),
            }
            assert (
                db.query(MarketPrice)
                .filter(MarketPrice.ticker == "RELIANCE.NS")
                .count()
                == 3
            )
        finally:
            db.close()


def test_historical_prices_fetch_only_the_missing_trailing_range(tmp_path):
    class TrailingProvider(CountingProvider):
        def __init__(self):
            super().__init__()
            self.requests = []

        def get_ohlcv(self, tickers, start_date, end_date=None):
            self.requests.append((tickers, start_date, end_date))
            close = pd.Series(
                [102.0, 103.0],
                index=pd.to_datetime(["2024-01-03", "2024-01-04"]),
            )
            return pd.DataFrame(
                {
                    "Open": close,
                    "High": close + 1,
                    "Low": close - 1,
                    "Close": close,
                    "Volume": 1000,
                },
                index=close.index,
            )

    with build_client(tmp_path) as client:
        db = client.app.state.session_factory()
        provider = TrailingProvider()
        try:
            db.add_all(
                [
                    MarketPrice(
                        ticker="RELIANCE.NS",
                        date=row_date,
                        open=price,
                        high=price + 1,
                        low=price - 1,
                        close=price,
                        volume=1000,
                    )
                    for row_date, price in (
                        (date(2024, 1, 1), 100),
                        (date(2024, 1, 2), 101),
                    )
                ]
            )
            db.commit()

            records = MarketDataService(
                db,
                provider=provider,
                cache=InMemoryMarketDataCache(),
            ).get_historical_prices(
                ["RELIANCE.NS"],
                date(2024, 1, 1),
                date(2024, 1, 4),
            )

            assert provider.requests == [
                (["RELIANCE.NS"], date(2024, 1, 3), date(2024, 1, 4))
            ]
            assert len(records) == 4
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
