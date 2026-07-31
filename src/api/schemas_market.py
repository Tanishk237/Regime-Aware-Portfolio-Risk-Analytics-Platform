from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class HistoricalPricePoint(BaseModel):
    ticker: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: float
    volume: Optional[float] = None


class HistoricalPricesResponse(BaseModel):
    success: bool = True
    tickers: list[str]
    start_date: date
    end_date: Optional[date] = None
    prices: list[HistoricalPricePoint]


class LivePricePoint(BaseModel):
    ticker: str
    price: float
    name: Optional[str] = None


class LivePricesResponse(BaseModel):
    success: bool = True
    prices: list[LivePricePoint]


class VIXPoint(BaseModel):
    date: date
    vix: float
    vix_change: Optional[float] = None


class VIXHistoryResponse(BaseModel):
    success: bool = True
    start_date: date
    end_date: Optional[date] = None
    points: list[VIXPoint]


class FIIDIIFlowPoint(BaseModel):
    date: date
    fii: float
    dii: float
    net_flow: float
    fii_avg: Optional[float] = None
    dii_avg: Optional[float] = None
    net_flow_avg: Optional[float] = None


class FIIDIIFlowsResponse(BaseModel):
    success: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    points: list[FIIDIIFlowPoint]


class MarketIndexResponse(BaseModel):
    success: bool = True
    symbol: str
    start_date: date
    end_date: Optional[date] = None
    prices: list[HistoricalPricePoint]


class FeatureMatrixRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1)
    start_date: date
    end_date: Optional[date] = None
    weights: Optional[list[float]] = None

    @field_validator("tickers")
    @classmethod
    def normalize_tickers(cls, value: list[str]) -> list[str]:
        tickers = [ticker.strip().upper() for ticker in value if ticker.strip()]
        if not tickers:
            raise ValueError("At least one ticker is required.")
        return tickers

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, value: Optional[list[float]]) -> Optional[list[float]]:
        if value is None:
            return value
        if any(weight < 0 for weight in value):
            raise ValueError("Weights cannot be negative.")
        if sum(value) <= 0:
            raise ValueError("Weights must sum to a positive value.")
        return value


class FeatureMatrixRecord(BaseModel):
    date: date
    values: dict[str, float]


class FeatureValidationReport(BaseModel):
    is_valid: bool
    rows: int
    columns: int
    missing_values: int
    duplicate_index: int
    infinite_values: int
    feature_names: list[str]


class FeatureMatrixResponse(BaseModel):
    success: bool = True
    tickers: list[str]
    start_date: date
    end_date: Optional[date] = None
    columns: list[str]
    records: list[FeatureMatrixRecord]
    metadata: dict[str, Any]
    validation: FeatureValidationReport
