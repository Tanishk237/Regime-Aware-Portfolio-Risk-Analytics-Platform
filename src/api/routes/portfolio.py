from __future__ import annotations

import csv
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.api.errors import AppError
from src.api.routes.market import market_service
from src.api.schemas_portfolio import (
    PortfolioCreate,
    PortfolioCsvResolutionResponse,
    PortfolioDemoResponse,
    PortfolioCsvPreviewResponse,
    PortfolioRead,
    PortfolioSummary,
    PortfolioUpdate,
    PortfolioUploadResponse,
    PositionRead,
    TradeCreate,
    TradeRead,
    TradeUpdate,
    PortfolioReturnRead,
)
from src.database import get_db
from src.database.models import User
from src.config import Settings, get_settings
from src.portfolio.portfolio_service import PortfolioService
from src.portfolio.demo_service import PortfolioDemoService
from src.intelligence import invalidate_portfolio_intelligence
from src.auth.rate_limit import enforce_rate_limit, request_identity
from src.auth.workload import enforce_workload_rate_limit


router = APIRouter(
    prefix="/portfolio",
)


def configured_portfolio_service(db: Session, settings: Settings) -> PortfolioService:
    return PortfolioService(
        db,
        market_data_service=market_service(db, settings),
        max_csv_tickers=settings.market_data_max_tickers_per_request,
        max_resolution_changes=settings.csv_resolution_max_changes,
        max_portfolios_per_user=settings.portfolio_max_per_user,
        max_portfolios_per_guest=settings.portfolio_max_per_guest,
        max_trades_per_portfolio=settings.portfolio_max_trades,
        max_market_history_days=settings.market_data_max_history_days,
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
    )


def configured_demo_service(db: Session, settings: Settings) -> PortfolioDemoService:
    return PortfolioDemoService(
        db,
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
        max_history_days=settings.market_data_max_history_days,
        max_portfolios_per_user=settings.portfolio_max_per_user,
        max_portfolios_per_guest=settings.portfolio_max_per_guest,
    )


def enforce_portfolio_workload_limit(
    request: Request,
    db: Session,
    settings: Settings,
    user: User,
) -> None:
    enforce_workload_rate_limit(
        db,
        request=request,
        user=user,
        secret_key=settings.auth_secret_key,
        bucket="portfolio:workload",
        user_limit=settings.portfolio_workload_rate_limit,
        guest_limit=settings.portfolio_guest_workload_rate_limit,
        network_limit=settings.portfolio_ip_workload_rate_limit,
        window_seconds=settings.portfolio_workload_rate_limit_window_seconds,
    )


def enforce_csv_upload_limit(
    request: Request,
    db: Session,
    settings: Settings,
    user: User,
) -> None:
    for bucket, identity, limit in (
        ("csv:user", f"user:{user.id}", settings.csv_upload_rate_limit),
        ("csv:network", request_identity(request), settings.csv_upload_ip_rate_limit),
    ):
        enforce_rate_limit(
            db,
            bucket=bucket,
            identity=identity,
            limit=limit,
            window_seconds=settings.csv_upload_rate_limit_window_seconds,
            secret_key=settings.auth_secret_key,
        )


def validate_csv_shape(csv_text: str, settings: Settings) -> None:
    row_count = 0
    cell_count = 0
    try:
        for row in csv.reader(StringIO(csv_text)):
            row_count += 1
            cell_count += len(row)
            if len(row) > settings.csv_upload_max_columns:
                raise AppError(
                    "CSV has too many columns.",
                    code="CSV_TOO_MANY_COLUMNS",
                    status_code=422,
                    details={"maximum": settings.csv_upload_max_columns},
                )
            if any(len(field) > settings.csv_upload_max_field_characters for field in row):
                raise AppError(
                    "CSV contains a field that is too long.",
                    code="CSV_FIELD_TOO_LONG",
                    status_code=422,
                    details={"maximum_characters": settings.csv_upload_max_field_characters},
                )
            if row_count - 1 > settings.csv_upload_max_rows:
                raise AppError(
                    "CSV has too many trade rows.",
                    code="CSV_TOO_MANY_ROWS",
                    status_code=422,
                    details={"maximum": settings.csv_upload_max_rows},
                )
            if cell_count > settings.csv_upload_max_cells:
                raise AppError(
                    "CSV contains too many cells.",
                    code="CSV_TOO_MANY_CELLS",
                    status_code=422,
                    details={"maximum": settings.csv_upload_max_cells},
                )
    except csv.Error as exc:
        raise AppError("Invalid CSV file.", code="INVALID_CSV", status_code=400) from exc


async def read_csv_upload(file: UploadFile, settings: Settings) -> str:
    content = await file.read(settings.csv_upload_max_bytes + 1)
    if len(content) > settings.csv_upload_max_bytes:
        raise AppError(
            "CSV file is too large.",
            code="CSV_TOO_LARGE",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            details={"max_bytes": settings.csv_upload_max_bytes},
        )
    if not content.strip():
        raise AppError(
            "CSV file is empty.",
            code="CSV_EMPTY",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            "CSV file must use UTF-8 encoding.",
            code="CSV_INVALID_ENCODING",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc
    validate_csv_shape(csv_text, settings)
    return csv_text


@router.get("", response_model=list[PortfolioRead])
def list_portfolios(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    return PortfolioService(db).list_portfolios(user)


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
    enforce_portfolio_workload_limit(request, db, settings, user)
    return configured_portfolio_service(db, settings).create_portfolio(
        user,
        name=payload.name,
        description=payload.description,
        base_currency=payload.base_currency,
        benchmark=payload.benchmark,
    )


@router.post("/demo", response_model=PortfolioDemoResponse, status_code=status.HTTP_201_CREATED)
def create_demo_portfolio(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioDemoResponse:
    enforce_portfolio_workload_limit(request, db, settings, user)
    portfolio, trades_created, analytics_precomputed = configured_demo_service(
        db, settings
    ).create_demo_portfolio(user)
    invalidate_portfolio_intelligence(db, portfolio.id)
    return PortfolioDemoResponse(
        portfolio=portfolio,
        trades_created=trades_created,
        analytics_precomputed=analytics_precomputed,
    )


@router.post("/demo/reset", response_model=PortfolioDemoResponse)
def reset_demo_portfolio(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioDemoResponse:
    enforce_portfolio_workload_limit(request, db, settings, user)
    portfolio, trades_created, analytics_precomputed = configured_demo_service(
        db, settings
    ).create_demo_portfolio(
        user,
        reset=True,
    )
    invalidate_portfolio_intelligence(db, portfolio.id)
    return PortfolioDemoResponse(
        portfolio=portfolio,
        trades_created=trades_created,
        analytics_precomputed=analytics_precomputed,
    )


@router.post("/upload", response_model=PortfolioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_portfolio(
    request: Request,
    name: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(default=None, max_length=2000),
    base_currency: str = Form(default="INR", min_length=3, max_length=12),
    benchmark: str = Form(default="NIFTY50", min_length=1, max_length=64),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioUploadResponse:
    enforce_csv_upload_limit(request, db, settings, user)
    csv_text = await read_csv_upload(file, settings)
    portfolio, trades, positions = configured_portfolio_service(db, settings).upload_trades_csv(
        user,
        name=name,
        description=description,
        base_currency=base_currency,
        benchmark=benchmark,
        csv_text=csv_text,
    )
    invalidate_portfolio_intelligence(db, portfolio.id)

    return PortfolioUploadResponse(
        portfolio=portfolio,
        trades_created=len(trades),
        positions=positions,
    )


@router.post("/upload/preview", response_model=PortfolioCsvPreviewResponse)
async def preview_portfolio_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioCsvPreviewResponse:
    enforce_csv_upload_limit(request, db, settings, user)
    csv_text = await read_csv_upload(file, settings)
    return PortfolioCsvPreviewResponse(
        **configured_portfolio_service(db, settings).preview_trades_csv(csv_text)
    )


@router.post("/upload/resolve", response_model=PortfolioCsvResolutionResponse)
async def resolve_portfolio_upload(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioCsvResolutionResponse:
    enforce_csv_upload_limit(request, db, settings, user)
    csv_text = await read_csv_upload(file, settings)
    return PortfolioCsvResolutionResponse(
        **configured_portfolio_service(db, settings).resolve_trades_csv(csv_text)
    )


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> object:
    return PortfolioService(db).get_portfolio(
        user,
        portfolio_id,
    )


@router.put("/{portfolio_id}", response_model=PortfolioRead)
def update_portfolio(
    portfolio_id: int,
    payload: PortfolioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
    enforce_portfolio_workload_limit(request, db, settings, user)
    provided_fields = payload.model_fields_set

    portfolio = PortfolioService(db).update_portfolio(
        user,
        portfolio_id,
        name=payload.name,
        description=payload.description,
        base_currency=payload.base_currency,
        benchmark=payload.benchmark,
        update_description="description" in provided_fields,
    )
    invalidate_portfolio_intelligence(db, portfolio_id)
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> None:
    enforce_portfolio_workload_limit(request, db, settings, user)
    PortfolioService(db).delete_portfolio(
        user,
        portfolio_id,
    )
    invalidate_portfolio_intelligence(db, portfolio_id)


@router.get("/{portfolio_id}/trades", response_model=list[TradeRead])
def list_trades(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    return PortfolioService(db).list_trades(
        user,
        portfolio_id,
    )


@router.post("/{portfolio_id}/trades", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
def add_trade(
    portfolio_id: int,
    payload: TradeCreate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
    enforce_portfolio_workload_limit(request, db, settings, user)
    trade = configured_portfolio_service(db, settings).add_trade(
        user,
        portfolio_id,
        ticker=payload.ticker,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        price=payload.price,
        transaction_date=payload.transaction_date,
        broker=payload.broker,
        fees=payload.fees,
        taxes=payload.taxes,
        currency=payload.currency,
        notes=payload.notes,
    )
    invalidate_portfolio_intelligence(db, portfolio_id)
    return trade


@router.put("/{portfolio_id}/trades/{trade_id}", response_model=TradeRead)
def update_trade(
    portfolio_id: int,
    trade_id: int,
    payload: TradeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
    enforce_portfolio_workload_limit(request, db, settings, user)
    trade = configured_portfolio_service(db, settings).update_trade(
        user,
        portfolio_id,
        trade_id,
        **payload.model_dump(exclude_unset=True),
    )
    invalidate_portfolio_intelligence(db, portfolio_id)
    return trade


@router.delete("/{portfolio_id}/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(
    portfolio_id: int,
    trade_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> None:
    enforce_portfolio_workload_limit(request, db, settings, user)
    configured_portfolio_service(db, settings).delete_trade(
        user,
        portfolio_id,
        trade_id,
    )
    invalidate_portfolio_intelligence(db, portfolio_id)


@router.get("/{portfolio_id}/positions", response_model=list[PositionRead])
def list_positions(
    portfolio_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> list:
    enforce_portfolio_workload_limit(request, db, settings, user)
    return configured_portfolio_service(db, settings).list_positions(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/returns", response_model=list[PortfolioReturnRead])
def list_returns(
    portfolio_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> list:
    enforce_portfolio_workload_limit(request, db, settings, user)
    return configured_portfolio_service(db, settings).list_returns(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
def portfolio_summary(
    portfolio_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> dict:
    enforce_portfolio_workload_limit(request, db, settings, user)
    return configured_portfolio_service(db, settings).build_summary(
        user,
        portfolio_id,
    )
