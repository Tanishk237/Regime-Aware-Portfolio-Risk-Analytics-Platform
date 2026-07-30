from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    base_currency: str = Field(default="INR", min_length=3, max_length=12)
    benchmark: str = Field(default="NIFTY50", min_length=1, max_length=64)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=12)
    benchmark: Optional[str] = Field(default=None, min_length=1, max_length=64)


class PortfolioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    base_currency: str
    benchmark: str
    created_at: datetime
    updated_at: datetime


class TradeCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    transaction_type: Literal["BUY", "SELL"] = "BUY"
    quantity: float = Field(gt=0)
    price: float = Field(gt=0)
    transaction_date: date
    broker: Optional[str] = None
    fees: float = Field(default=0.0, ge=0)
    taxes: float = Field(default=0.0, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=12)
    notes: Optional[str] = None


class TradeUpdate(BaseModel):
    ticker: Optional[str] = Field(default=None, min_length=1, max_length=32)
    transaction_type: Optional[Literal["BUY", "SELL"]] = None
    quantity: Optional[float] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    transaction_date: Optional[date] = None
    broker: Optional[str] = None
    fees: Optional[float] = Field(default=None, ge=0)
    taxes: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=12)
    notes: Optional[str] = None


class TradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    transaction_type: str
    quantity: float
    price: float
    transaction_date: date
    broker: Optional[str] = None
    fees: float
    taxes: float
    currency: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    quantity: float
    avg_cost: float
    cost_basis: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    market_weight: Optional[float] = None
    cost_weight: Optional[float] = None
    unrealized_pnl: float
    realized_pnl: float
    updated_at: datetime


class PortfolioReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    date: date
    daily_return: float
    cumulative_return: Optional[float] = None
    portfolio_value: Optional[float] = None
    created_at: datetime


class PortfolioSummary(BaseModel):
    portfolio_id: int
    name: str
    base_currency: str
    trades_count: int
    positions_count: int
    invested_value: float
    current_value: Optional[float] = None
    unrealized_profit: Optional[float] = None
    unrealized_profit_pct: Optional[float] = None
    realized_profit: float
    latest_return: Optional[float] = None
    total_return: Optional[float] = None


class PortfolioUploadResponse(BaseModel):
    portfolio: PortfolioRead
    trades_created: int
    positions: list[PositionRead]
