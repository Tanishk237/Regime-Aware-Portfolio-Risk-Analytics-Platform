from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from src.database.base import Base
from src.database.models import MarketPrice
from src.market.fetch_service import MarketDataFetchService
from src.market import MarketDataService
from src.market.providers import DeterministicTestProvider
from src.portfolio.market_valuation_service import PortfolioMarketValuationService


def test_latest_prices_use_one_query_and_exclude_demo_quotes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for ticker in ("INFY.NS", "TCS.NS", "SBIN.NS"):
            for day, close, source in ((1, 100, "provider"), (2, 120, "provider"), (3, 999, "demo")):
                db.add(MarketPrice(ticker=ticker, date=date(2026, 1, day), open=close, high=close, low=close, close=close, volume=100, data_source=source))
        db.commit()
        queries = []
        event.listen(engine, "before_cursor_execute", lambda *args: queries.append(args[2]))
        service = PortfolioMarketValuationService()
        service.db = db
        result = service._latest_prices_by_ticker(["INFY.NS", "TCS.NS", "SBIN.NS"], False)
        assert result == {"INFY.NS": 120, "TCS.NS": 120, "SBIN.NS": 120}
        assert len(queries) == 1
        assert service._latest_prices_by_ticker(["INFY.NS"], True) == {"INFY.NS": 999}
    engine.dispose()


def test_matching_history_ranges_share_one_provider_request():
    service = MarketDataFetchService()
    start, end = date(2026, 1, 1), date(2026, 1, 5)
    service._missing_price_ranges = lambda *args: [(start, end)]
    service.provider = SimpleNamespace(get_ohlcv=Mock(return_value="provider-frame"))
    service._normalize_ohlcv = lambda frame, tickers: [
        {"ticker": ticker, "date": start, "close": index + 100}
        for index, ticker in enumerate(tickers)
    ]
    symbols = ["INFY.NS", "TCS.NS", "SBIN.NS"]
    result = service._fetch_missing_price_records(symbols, start, end, [])
    service.provider.get_ohlcv.assert_called_once_with(symbols, start, end)
    assert [item["close"] for item in result] == [100, 101, 102]


def test_fixture_batch_preserves_each_tickers_prices():
    provider = DeterministicTestProvider()
    service = MarketDataService.__new__(MarketDataService)
    symbols = ["INFY.NS", "TCS.NS"]
    start, end = date(2026, 1, 1), date(2026, 1, 5)
    frame = provider.get_ohlcv(symbols, start, end)
    records = service._normalize_ohlcv(frame, symbols)
    for ticker in symbols:
        actual = [row["close"] for row in records if row["ticker"] == ticker]
        expected = provider.get_ohlcv([ticker], start, end)["Close"].tolist()
        assert actual == expected
