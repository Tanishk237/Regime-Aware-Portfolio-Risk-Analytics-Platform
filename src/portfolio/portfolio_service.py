from typing import Optional

from sqlalchemy.orm import Session

from src.market import MarketDataService
from src.portfolio.crud_service import PortfolioCrudService
from src.portfolio.csv_import_service import PortfolioCsvImportService
from src.portfolio.market_valuation_service import PortfolioMarketValuationService
from src.portfolio.position_service import PortfolioPositionService
from src.portfolio.trade_service import PortfolioTradeService


class PortfolioService(
    PortfolioCrudService,
    PortfolioMarketValuationService,
    PortfolioTradeService,
    PortfolioPositionService,
    PortfolioCsvImportService,
):
    def __init__(
        self,
        db: Session,
        *,
        market_data_service: Optional[MarketDataService] = None,
        max_csv_tickers: int = 20,
        max_resolution_changes: int = 2_000,
        max_portfolios_per_user: int = 50,
        max_portfolios_per_guest: int = 5,
        max_trades_per_portfolio: int = 10_000,
        max_market_history_days: int = 3_650,
        runtime_hmm_fit_enabled: bool = True,
        max_regime_observations: int = 1_500,
    ):
        self.db = db
        self.market_data_service = market_data_service or MarketDataService(db)
        self.max_csv_tickers = max_csv_tickers
        self.max_resolution_changes = max_resolution_changes
        self.max_portfolios_per_user = max_portfolios_per_user
        self.max_portfolios_per_guest = max_portfolios_per_guest
        self.max_trades_per_portfolio = max_trades_per_portfolio
        self.max_market_history_days = max_market_history_days
        self.runtime_hmm_fit_enabled = runtime_hmm_fit_enabled
        self.max_regime_observations = max_regime_observations
        self._repair_change_count = 0
