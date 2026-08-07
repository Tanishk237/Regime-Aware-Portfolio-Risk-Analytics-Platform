from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.analytics import AnalyticsService
from src.api.dependencies import get_or_create_default_user
from src.api.routes.market import market_service
from src.api.schemas_analytics import (
    RegimeAnalyticsRequest,
    RegimeAnalyticsResponse,
    RiskAnalyticsResponse,
)
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User


router = APIRouter(prefix="/analytics")


def current_user(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    return get_or_create_default_user(db, settings)


@router.get("/portfolio/{portfolio_id}/risk", response_model=RiskAnalyticsResponse)
def risk_analytics(
    portfolio_id: int,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    confidence_level: float = Query(default=0.95, gt=0, lt=1),
    risk_free_rate: float = Query(default=0.06),
    rolling_window: int = Query(default=20, gt=1),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(current_user),
) -> RiskAnalyticsResponse:
    payload = AnalyticsService(
        db,
        market_data_service=market_service(db, settings),
    ).build_risk_payload(
        user,
        portfolio_id,
        start_date=start_date,
        end_date=end_date,
        confidence_level=confidence_level,
        risk_free_rate=risk_free_rate,
        rolling_window=rolling_window,
        persist=persist,
    )
    return RiskAnalyticsResponse(**payload)


@router.post("/portfolio/{portfolio_id}/regime", response_model=RegimeAnalyticsResponse)
def regime_analytics(
    portfolio_id: int,
    payload: RegimeAnalyticsRequest,
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(current_user),
) -> RegimeAnalyticsResponse:
    result = AnalyticsService(
        db,
        market_data_service=market_service(db, settings),
        model_dir=settings.regime_model_dir,
    ).build_regime_payload(
        user,
        portfolio_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        weights=payload.weights,
        persist=persist,
    )
    return RegimeAnalyticsResponse(**result)
