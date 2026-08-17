from __future__ import annotations

from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.market.cache import InMemoryMarketDataCache, MarketDataCache
from src.market.feature_service import MarketFeatureService
from src.market.fetch_service import MarketDataFetchService
from src.market.normalizers import MarketDataNormalizers
from src.market.persistence import MarketDataPersistence
from src.market.providers import MarketDataProvider, build_market_data_provider
from src.market.utils import MarketDataUtils


class MarketDataService(
    MarketDataUtils,
    MarketDataNormalizers,
    MarketDataPersistence,
    MarketDataFetchService,
    MarketFeatureService,
):
    def __init__(
        self,
        db: Session,
        *,
        default_fii_dii_path: str = "data/external/fii_dii.csv",
        provider: Optional[MarketDataProvider] = None,
        provider_name: str = "yahoo",
        cache: Optional[MarketDataCache] = None,
        cache_ttl_seconds: int = 900,
        provider_retries: int = 3,
        provider_retry_backoff_seconds: float = 0.25,
    ):
        self.db = db
        self.default_fii_dii_path = Path(default_fii_dii_path)
        self.provider = provider or build_market_data_provider(
            provider_name,
            retries=provider_retries,
            retry_backoff_seconds=provider_retry_backoff_seconds,
        )
        self.cache = cache or InMemoryMarketDataCache()
        self.cache_ttl_seconds = cache_ttl_seconds
