from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_or_create_default_user
from src.api.schemas_portfolio import (
    PortfolioCreate,
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
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User
from src.portfolio.portfolio_service import PortfolioService


router = APIRouter(
    prefix="/portfolio",
)


def current_user(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    return get_or_create_default_user(
        db,
        settings,
    )


@router.get("", response_model=list[PortfolioRead])
def list_portfolios(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list:
    return PortfolioService(db).list_portfolios(user)


@router.post("", response_model=PortfolioRead, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> object:
    return PortfolioService(db).create_portfolio(
        user,
        name=payload.name,
        description=payload.description,
        base_currency=payload.base_currency,
        benchmark=payload.benchmark,
    )


@router.post("/upload", response_model=PortfolioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_portfolio(
    name: str = Form(...),
    description: Optional[str] = Form(default=None),
    base_currency: str = Form(default="INR"),
    benchmark: str = Form(default="NIFTY50"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> PortfolioUploadResponse:
    csv_text = (
        await file.read()
    ).decode("utf-8")
    portfolio, trades, positions = PortfolioService(db).upload_trades_csv(
        user,
        name=name,
        description=description,
        base_currency=base_currency,
        benchmark=benchmark,
        csv_text=csv_text,
    )

    return PortfolioUploadResponse(
        portfolio=portfolio,
        trades_created=len(trades),
        positions=positions,
    )


@router.get("/{portfolio_id}", response_model=PortfolioRead)
def get_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
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
    user: User = Depends(current_user),
) -> object:
    provided_fields = payload.model_fields_set

    return PortfolioService(db).update_portfolio(
        user,
        portfolio_id,
        name=payload.name,
        description=payload.description,
        base_currency=payload.base_currency,
        benchmark=payload.benchmark,
        update_description="description" in provided_fields,
    )


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    PortfolioService(db).delete_portfolio(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/trades", response_model=list[TradeRead])
def list_trades(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
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
    user: User = Depends(current_user),
) -> object:
    return PortfolioService(db).add_trade(
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


@router.put("/{portfolio_id}/trades/{trade_id}", response_model=TradeRead)
def update_trade(
    portfolio_id: int,
    trade_id: int,
    payload: TradeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> object:
    return PortfolioService(db).update_trade(
        user,
        portfolio_id,
        trade_id,
        **payload.model_dump(exclude_unset=True),
    )


@router.delete("/{portfolio_id}/trades/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trade(
    portfolio_id: int,
    trade_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> None:
    PortfolioService(db).delete_trade(
        user,
        portfolio_id,
        trade_id,
    )


@router.get("/{portfolio_id}/positions", response_model=list[PositionRead])
def list_positions(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list:
    return PortfolioService(db).list_positions(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/returns", response_model=list[PortfolioReturnRead])
def list_returns(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> list:
    return PortfolioService(db).list_returns(
        user,
        portfolio_id,
    )


@router.get("/{portfolio_id}/summary", response_model=PortfolioSummary)
def portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
) -> dict:
    return PortfolioService(db).build_summary(
        user,
        portfolio_id,
    )
