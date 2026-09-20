from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
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
from src.api.dependencies import get_current_user
from src.api.errors import AppError
from src.auth.rate_limit import enforce_rate_limit, request_identity
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User
from src.market import MarketDataService
from src.market.cache import market_data_cache


router = APIRouter(
    prefix="/market",
)


def parse_tickers(value: str, *, limit: int) -> list[str]:
    tickers = [ticker.strip() for ticker in value.split(",") if ticker.strip()]
    if not tickers:
        raise AppError("At least one ticker is required.", code="TICKERS_REQUIRED", status_code=422)
    if len(tickers) > limit:
        raise AppError(
            "Too many tickers were requested.",
            code="TOO_MANY_TICKERS",
            status_code=422,
            details={"maximum": limit},
        )
    return tickers


def enforce_market_limit(
    db: Session,
    settings: Settings,
    *,
    request: Request,
    user: User | None = None,
    public: bool = False,
) -> None:
    if public:
        enforce_rate_limit(
            db,
            bucket="market:public",
            identity=request_identity(request),
            limit=settings.market_public_rate_limit,
            window_seconds=settings.market_rate_limit_window_seconds,
            secret_key=settings.auth_secret_key,
        )
        return
    if user is None:
        raise RuntimeError("Authenticated market limits require a user")
    for bucket, identity, limit in (
        ("market:user", f"user:{user.id}", settings.market_user_rate_limit),
        ("market:network", request_identity(request), settings.market_ip_rate_limit),
    ):
        enforce_rate_limit(
            db,
            bucket=bucket,
            identity=identity,
            limit=limit,
            window_seconds=settings.market_rate_limit_window_seconds,
            secret_key=settings.auth_secret_key,
        )


def validate_market_window(start_date: date, end_date: Optional[date], settings: Settings) -> None:
    final_date = end_date or date.today()
    if (final_date - start_date).days > settings.market_data_max_history_days:
        raise AppError(
            "The requested market-data window is too large.",
            code="MARKET_DATA_WINDOW_TOO_LARGE",
            status_code=422,
            details={"maximum_days": settings.market_data_max_history_days},
        )


def market_service(db: Session, settings: Settings) -> MarketDataService:
    return MarketDataService(
        db,
        default_fii_dii_path=settings.fii_dii_csv_path,
        provider_name=settings.market_data_provider,
        cache=market_data_cache,
        cache_ttl_seconds=settings.market_data_cache_ttl_seconds,
        provider_retries=settings.market_data_provider_retries,
        provider_retry_backoff_seconds=settings.market_data_provider_retry_backoff_seconds,
        instrument_metadata_ttl_days=settings.instrument_metadata_ttl_days,
    )


@router.get("/historical-prices", response_model=HistoricalPricesResponse)
def historical_prices(
    request: Request,
    tickers: str = Query(..., description="Comma-separated ticker symbols."),
    start_date: date = Query(...),
    end_date: Optional[date] = Query(default=None),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> HistoricalPricesResponse:
    enforce_market_limit(db, settings, request=request, user=user)
    validate_market_window(start_date, end_date, settings)
    parsed_tickers = parse_tickers(tickers, limit=settings.market_data_max_tickers_per_request)
    service = market_service(db, settings)
    records = service.get_historical_prices(
        parsed_tickers,
        start_date,
        end_date,
        persist=persist,
    )
    metadata = service.fetch_metadata.get("historical", {})
    return HistoricalPricesResponse(
        tickers=sorted({record["ticker"] for record in records}),
        start_date=start_date,
        end_date=end_date,
        prices=records,
        source=str(metadata.get("source", "unknown")),
        fallback_used=bool(metadata.get("fallback_used", False)),
        coverage_complete=bool(metadata.get("coverage_complete", False)),
        as_of=metadata.get("as_of"),
    )


@router.get("/live-prices", response_model=LivePricesResponse)
def live_prices(
    request: Request,
    tickers: str = Query(..., description="Comma-separated ticker symbols."),
    include_name: bool = Query(default=False),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LivePricesResponse:
    enforce_market_limit(
        db,
        settings,
        request=request,
        public=True,
    )
    records = market_service(db, settings).get_live_prices(
        parse_tickers(tickers, limit=settings.market_data_max_tickers_per_request),
        include_name=include_name,
    )
    return LivePricesResponse(prices=records)


@router.get("/india-vix", response_model=VIXHistoryResponse)
def india_vix(
    request: Request,
    start_date: date = Query(...),
    end_date: Optional[date] = Query(default=None),
    window: int = Query(default=5, gt=0),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> VIXHistoryResponse:
    enforce_market_limit(db, settings, request=request, user=user)
    validate_market_window(start_date, end_date, settings)
    service = market_service(db, settings)
    records = service.get_india_vix(
        start_date,
        end_date,
        window=window,
        persist=persist,
    )
    metadata = service.fetch_metadata.get("vix", {})
    return VIXHistoryResponse(
        start_date=start_date,
        end_date=end_date,
        points=records,
        source=str(metadata.get("source", "unknown")),
        fallback_used=bool(metadata.get("fallback_used", False)),
        coverage_complete=bool(metadata.get("coverage_complete", False)),
        as_of=metadata.get("as_of"),
    )


@router.get("/fii-dii-flows", response_model=FIIDIIFlowsResponse)
def fii_dii_flows(
    request: Request,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    window: int = Query(default=20, gt=0),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> FIIDIIFlowsResponse:
    enforce_market_limit(db, settings, request=request, user=user)
    if start_date is not None:
        validate_market_window(start_date, end_date, settings)
    records = market_service(db, settings).get_fii_dii_flows(
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
    request: Request,
    symbol: str = Query(default="^NSEI"),
    start_date: date = Query(...),
    end_date: Optional[date] = Query(default=None),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> MarketIndexResponse:
    enforce_market_limit(db, settings, request=request, user=user)
    validate_market_window(start_date, end_date, settings)
    records = market_service(db, settings).get_market_index_data(
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
    request: Request,
    payload: FeatureMatrixRequest,
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> FeatureMatrixResponse:
    enforce_market_limit(db, settings, request=request, user=user)
    validate_market_window(payload.start_date, payload.end_date, settings)
    result = market_service(db, settings).build_feature_matrix(
        tickers=payload.tickers,
        start_date=payload.start_date,
        end_date=payload.end_date,
        weights=payload.weights,
        persist=persist,
    )
    return FeatureMatrixResponse(**result)
