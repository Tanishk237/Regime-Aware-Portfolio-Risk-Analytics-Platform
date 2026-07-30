from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: Optional[str] = None
    created_at: datetime


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    base_currency: str = Field(default="INR", min_length=3, max_length=12)


class PortfolioUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    base_currency: Optional[str] = Field(default=None, min_length=3, max_length=12)


class PortfolioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    base_currency: str
    created_at: datetime
    updated_at: datetime


class TradeCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=32)
    shares: float = Field(gt=0)
    buy_date: date
    buy_price: float = Field(gt=0)
    notes: Optional[str] = None


class TradeUpdate(BaseModel):
    ticker: Optional[str] = Field(default=None, min_length=1, max_length=32)
    shares: Optional[float] = Field(default=None, gt=0)
    buy_date: Optional[date] = None
    buy_price: Optional[float] = Field(default=None, gt=0)
    notes: Optional[str] = None


class TradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    shares: float
    buy_date: date
    buy_price: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    ticker: str
    shares: float
    avg_cost: float
    cost_basis: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    market_weight: Optional[float] = None
    cost_weight: Optional[float] = None
    updated_at: datetime


class PortfolioReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    portfolio_id: int
    date: date
    return_value: float
    cumulative_return: Optional[float] = None
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
    latest_return: Optional[float] = None
    total_return: Optional[float] = None


class PortfolioUploadResponse(BaseModel):
    portfolio: PortfolioRead
    trades_created: int
    positions: list[PositionRead]
