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
    ):
        self.db = db
        self.market_data_service = market_data_service or MarketDataService(db)
