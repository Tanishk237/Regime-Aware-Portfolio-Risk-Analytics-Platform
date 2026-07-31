from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.schemas_market import (
    FIIDIIFlowsResponse,
    FeatureMatrixRequest,
    FeatureMatrixResponse,
    HistoricalPricesResponse,
    LivePricesResponse,
    MarketIndexResponse,
    VIXHistoryResponse,
)
from src.config import Settings, get_settings
from src.database import get_db
from src.market import MarketDataService


router = APIRouter(
    prefix="/market",
)


def parse_tickers(value: str) -> list[str]:
    return [ticker.strip() for ticker in value.split(",") if ticker.strip()]


@router.get("/historical-prices", response_model=HistoricalPricesResponse)
def historical_prices(
    tickers: str = Query(..., description="Comma-separated ticker symbols."),
    start_date: date = Query(...),
    end_date: Optional[date] = Query(default=None),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HistoricalPricesResponse:
    parsed_tickers = parse_tickers(tickers)
    records = MarketDataService(db, default_fii_dii_path=settings.fii_dii_csv_path).get_historical_prices(
        parsed_tickers,
        start_date,
        end_date,
        persist=persist,
    )
    return HistoricalPricesResponse(
        tickers=sorted({record["ticker"] for record in records}),
        start_date=start_date,
        end_date=end_date,
        prices=records,
    )


@router.get("/live-prices", response_model=LivePricesResponse)
def live_prices(
    tickers: str = Query(..., description="Comma-separated ticker symbols."),
    include_name: bool = Query(default=False),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LivePricesResponse:
    records = MarketDataService(db, default_fii_dii_path=settings.fii_dii_csv_path).get_live_prices(
        parse_tickers(tickers),
        include_name=include_name,
    )
    return LivePricesResponse(prices=records)


@router.get("/india-vix", response_model=VIXHistoryResponse)
def india_vix(
    start_date: date = Query(...),
    end_date: Optional[date] = Query(default=None),
    window: int = Query(default=5, gt=0),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> VIXHistoryResponse:
    records = MarketDataService(db, default_fii_dii_path=settings.fii_dii_csv_path).get_india_vix(
        start_date,
        end_date,
        window=window,
        persist=persist,
    )
    return VIXHistoryResponse(
        start_date=start_date,
        end_date=end_date,
        points=records,
    )


@router.get("/fii-dii-flows", response_model=FIIDIIFlowsResponse)
def fii_dii_flows(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    window: int = Query(default=20, gt=0),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FIIDIIFlowsResponse:
    records = MarketDataService(db, default_fii_dii_path=settings.fii_dii_csv_path).get_fii_dii_flows(
        start_date=start_date,
        end_date=end_date,
        window=window,
        persist=persist,
    )
    return FIIDIIFlowsResponse(
        start_date=start_date,
        end_date=end_date,
        points=records,
    )


@router.get("/index-data", response_model=MarketIndexResponse)
def market_index_data(
    symbol: str = Query(default="^NSEI"),
    start_date: date = Query(...),
    end_date: Optional[date] = Query(default=None),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> MarketIndexResponse:
    records = MarketDataService(db, default_fii_dii_path=settings.fii_dii_csv_path).get_market_index_data(
        symbol,
        start_date,
        end_date,
        persist=persist,
    )
    return MarketIndexResponse(
        symbol=records[0]["ticker"] if records else symbol,
        start_date=start_date,
        end_date=end_date,
        prices=records,
    )


@router.post(
    "/features/matrix",
    response_model=FeatureMatrixResponse,
    status_code=status.HTTP_200_OK,
)
def feature_matrix(
    payload: FeatureMatrixRequest,
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FeatureMatrixResponse:
    result = MarketDataService(db, default_fii_dii_path=settings.fii_dii_csv_path).build_feature_matrix(
        tickers=payload.tickers,
        start_date=payload.start_date,
        end_date=payload.end_date,
        weights=payload.weights,
        persist=persist,
    )
    return FeatureMatrixResponse(**result)
