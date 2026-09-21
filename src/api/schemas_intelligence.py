from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


Severity = Literal["high", "medium", "low"]


class RiskProfileUpdate(BaseModel):
    tolerance: Literal["conservative", "moderate", "aggressive"] = "moderate"
    horizon_months: int = Field(default=60, ge=1, le=600)
    max_drawdown_tolerance: float = Field(default=0.20, ge=0.01, le=0.90)
    liquidity_needs: Literal["low", "medium", "high"] = "medium"
    income_requirement: Optional[str] = Field(default=None, max_length=1000)
    restrictions: list[str] = Field(default_factory=list, max_length=30)


class RiskProfileRead(RiskProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class Citation(BaseModel):
    label: str
    value: str
    source: str
    as_of: Optional[date] = None


class RecommendationRead(BaseModel):
    id: int
    fingerprint: str
    severity: Severity
    category: str
    title: str
    description: str
    evidence: str
    action: str
    expected_impact: str
    confidence: float
    is_read: bool
    created_at: datetime


class ReadStateUpdate(BaseModel):
    is_read: bool


class AlertRead(BaseModel):
    id: int
    alert_type: str
    severity: Severity
    title: str
    description: str
    evidence: Optional[str] = None
    is_read: bool
    detected_at: datetime


class SectorAllocationRead(BaseModel):
    sector: str
    market_value: float
    weight: float
    holdings_count: int
    tickers: list[str]


class PortfolioIntelligenceResponse(BaseModel):
    portfolio_id: int
    data_as_of: Optional[date] = None
    summary: dict[str, Any]
    positions: list[dict[str, Any]]
    sector_allocation: list[SectorAllocationRead] = Field(default_factory=list)
    risk: Optional[dict[str, Any]] = None
    regime: Optional[dict[str, Any]] = None
    risk_profile: RiskProfileRead
    executive_summary: list[str]
    citations: list[Citation]
    warnings: list[str]
    recommendations: list[RecommendationRead]
    alerts: list[AlertRead]


class MetricExplanationResponse(BaseModel):
    metric: str
    title: str
    definition: str
    value: str
    interpretation: str
    why_it_matters: str
    source: str
    data_as_of: Optional[date] = None
    ask_prompt: str


class StressScenarioParseRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)


class StressScenarioPreview(BaseModel):
    name: str
    prompt: str
    market_shock: float = Field(ge=-100, le=100)
    volatility_shock: float = Field(ge=-100, le=500)
    ticker_shocks: dict[str, float] = Field(default_factory=dict)
    assumptions: list[str]
    requires_confirmation: bool = True


class StressScenarioRunRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    market_shock: float = Field(ge=-100, le=100)
    volatility_shock: float = Field(default=0, ge=-100, le=500)
    ticker_shocks: dict[str, float] = Field(default_factory=dict)
    confirmed: bool


class StressPositionImpact(BaseModel):
    ticker: str
    applied_shock: float
    value_before: float
    value_after: float
    impact: float


class StressScenarioResultResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    value_before: float
    value_after: float
    estimated_impact: float
    estimated_impact_pct: float
    historical_var_before: Optional[float] = None
    historical_var_after: Optional[float] = None
    position_impacts: list[StressPositionImpact]
    assumptions: list[str]
    generated_at: datetime
