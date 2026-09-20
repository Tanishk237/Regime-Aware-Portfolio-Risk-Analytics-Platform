from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.analytics import AnalyticsService
from src.api.dependencies import get_current_user
from src.api.routes.market import market_service
from src.api.schemas_analytics import (
    RegimeAnalyticsRequest,
    RegimeAnalyticsResponse,
    RiskAnalyticsResponse,
)
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User
from src.auth.workload import enforce_workload_rate_limit


router = APIRouter(prefix="/analytics")


def enforce_analytics_limit(
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
        bucket="analytics",
        user_limit=settings.analytics_rate_limit,
        guest_limit=settings.analytics_guest_rate_limit,
        network_limit=settings.analytics_ip_rate_limit,
        window_seconds=settings.analytics_rate_limit_window_seconds,
    )


@router.get("/portfolio/{portfolio_id}/risk", response_model=RiskAnalyticsResponse)
def risk_analytics(
    request: Request,
    portfolio_id: int,
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    confidence_level: float = Query(default=0.95, gt=0, lt=1),
    risk_free_rate: float = Query(default=0.06),
    rolling_window: int = Query(default=20, gt=1),
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> RiskAnalyticsResponse:
    enforce_analytics_limit(request, db, settings, user)
    payload = AnalyticsService(
        db,
        market_data_service=market_service(db, settings),
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
        max_history_days=settings.market_data_max_history_days,
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
    request: Request,
    portfolio_id: int,
    payload: RegimeAnalyticsRequest,
    persist: bool = Query(default=True),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> RegimeAnalyticsResponse:
    enforce_analytics_limit(request, db, settings, user)
    result = AnalyticsService(
        db,
        market_data_service=market_service(db, settings),
        model_dir=settings.regime_model_dir,
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
        max_history_days=settings.market_data_max_history_days,
    ).build_regime_payload(
        user,
        portfolio_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        weights=payload.weights,
        persist=persist,
    )
    return RegimeAnalyticsResponse(**result)
