from sqlalchemy.orm import Session

from src.portfolio.crud_service import PortfolioCrudService
from src.portfolio.csv_import_service import PortfolioCsvImportService
from src.portfolio.position_service import PortfolioPositionService
from src.portfolio.trade_service import PortfolioTradeService


class PortfolioService(
    PortfolioCrudService,
    PortfolioTradeService,
    PortfolioPositionService,
    PortfolioCsvImportService,
):
    def __init__(self, db: Session):
        self.db = db
