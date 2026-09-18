from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
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


router = APIRouter(
    prefix="/portfolio",
)


def configured_portfolio_service(db: Session, settings: Settings) -> PortfolioService:
    return PortfolioService(
        db,
        market_data_service=market_service(db, settings),
    )


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
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            "CSV file must use UTF-8 encoding.",
            code="CSV_INVALID_ENCODING",
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc


@router.get("", response_model=list[PortfolioRead])
def list_portfolios(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    return PortfolioService(db).list_portfolios(user)


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> object:
    return PortfolioService(db).create_portfolio(
        user,
        name=payload.name,
        description=payload.description,
        base_currency=payload.base_currency,
        benchmark=payload.benchmark,
    )


@router.post("/demo", response_model=PortfolioDemoResponse, status_code=status.HTTP_201_CREATED)
def create_demo_portfolio(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PortfolioDemoResponse:
    portfolio, trades_created, analytics_precomputed = PortfolioDemoService(db).create_demo_portfolio(user)
    invalidate_portfolio_intelligence(db, portfolio.id)
    return PortfolioDemoResponse(
        portfolio=portfolio,
        trades_created=trades_created,
        analytics_precomputed=analytics_precomputed,
    )


@router.post("/demo/reset", response_model=PortfolioDemoResponse)
def reset_demo_portfolio(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PortfolioDemoResponse:
    portfolio, trades_created, analytics_precomputed = PortfolioDemoService(db).create_demo_portfolio(
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
    name: str = Form(...),
    description: Optional[str] = Form(default=None),
    base_currency: str = Form(default="INR"),
    benchmark: str = Form(default="NIFTY50"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioUploadResponse:
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
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioCsvPreviewResponse:
    del user
    csv_text = await read_csv_upload(file, settings)
    return PortfolioCsvPreviewResponse(
        **PortfolioService(db).preview_trades_csv(csv_text)
    )


@router.post("/upload/resolve", response_model=PortfolioCsvResolutionResponse)
async def resolve_portfolio_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioCsvResolutionResponse:
    del user
    csv_text = await read_csv_upload(file, settings)
    return PortfolioCsvResolutionResponse(
        **PortfolioService(db).resolve_trades_csv(csv_text)
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> object:
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
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
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
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
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
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
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
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> None:
    configured_portfolio_service(db, settings).delete_trade(
        user,
        portfolio_id,
        trade_id,
    )
    invalidate_portfolio_intelligence(db, portfolio_id)


@router.get("/{portfolio_id}/positions", response_model=list[PositionRead])
def list_positions(
    portfolio_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> list:
    return configured_portfolio_service(db, settings).list_positions(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/returns", response_model=list[PortfolioReturnRead])
def list_returns(
    portfolio_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> list:
    return configured_portfolio_service(db, settings).list_returns(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
def portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> dict:
    return configured_portfolio_service(db, settings).build_summary(
        user,
        portfolio_id,
    )
