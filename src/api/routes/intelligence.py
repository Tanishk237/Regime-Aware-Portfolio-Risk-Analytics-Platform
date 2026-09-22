from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.api.routes.market import market_service
from src.api.schemas_intelligence import (
    AlertRead,
    MetricExplanationResponse,
    PortfolioIntelligenceResponse,
    ReadStateUpdate,
    RecommendationRead,
    RiskProfileRead,
    RiskProfileUpdate,
    StressScenarioParseRequest,
    StressScenarioPreview,
    StressScenarioResultResponse,
    StressScenarioRunRequest,
)
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User
from src.intelligence import (
    IntelligentStressService,
    PortfolioInsightService,
    PortfolioIntelligenceContextService,
    RecommendationService,
    RiskProfileService,
)
from src.auth.workload import enforce_workload_rate_limit


router = APIRouter(prefix="/intelligence")


def context_service(db: Session, settings: Settings) -> PortfolioIntelligenceContextService:
    return PortfolioIntelligenceContextService(
        db,
        market_data_service=market_service(db, settings),
        model_dir=settings.regime_model_dir,
        cache_ttl_seconds=settings.intelligence_cache_ttl_seconds,
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
        max_history_days=settings.market_data_max_history_days,
    )


def enforce_intelligence_limit(
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
        bucket="intelligence",
        user_limit=settings.analytics_rate_limit,
        guest_limit=settings.analytics_guest_rate_limit,
        network_limit=settings.analytics_ip_rate_limit,
        window_seconds=settings.analytics_rate_limit_window_seconds,
    )


@router.get("/profile", response_model=RiskProfileRead)
def get_risk_profile(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> RiskProfileRead:
    enforce_intelligence_limit(request, db, settings, user)
    return RiskProfileRead.model_validate(RiskProfileService(db).get_or_create(user))


@router.put("/profile", response_model=RiskProfileRead)
def update_risk_profile(
    payload: RiskProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> RiskProfileRead:
    enforce_intelligence_limit(request, db, settings, user)
    profile = RiskProfileService(db).update(user, **payload.model_dump())
    return RiskProfileRead.model_validate(profile)


@router.get("/portfolio/{portfolio_id}", response_model=PortfolioIntelligenceResponse)
def portfolio_intelligence(
    request: Request,
    portfolio_id: int,
    refresh: bool = False,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> PortfolioIntelligenceResponse:
    enforce_intelligence_limit(request, db, settings, user)
    builder = context_service(db, settings)
    context = (
        builder.build(user, portfolio_id, refresh=True)
        if refresh
        else builder.build(user, portfolio_id)
    )
    service = RecommendationService(db)
    recommendations = service.generate(user, portfolio_id, context)
    context["recommendations"] = [service.serialize(item) for item in recommendations]
    context["alerts"] = [
        service.serialize_alert(item) for item in service.list_alerts(user, portfolio_id)
    ]
    return PortfolioIntelligenceResponse(**context)


@router.get(
    "/portfolio/{portfolio_id}/explanations/{metric}",
    response_model=MetricExplanationResponse,
)
def explain_metric(
    request: Request,
    portfolio_id: int,
    metric: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> MetricExplanationResponse:
    enforce_intelligence_limit(request, db, settings, user)
    context = context_service(db, settings).build(user, portfolio_id)
    return MetricExplanationResponse(**PortfolioInsightService().explain(context, metric))


@router.get(
    "/portfolio/{portfolio_id}/recommendations",
    response_model=list[RecommendationRead],
)
def recommendations(
    request: Request,
    portfolio_id: int,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> list[RecommendationRead]:
    enforce_intelligence_limit(request, db, settings, user)
    context = context_service(db, settings).build(user, portfolio_id)
    service = RecommendationService(db)
    return [
        RecommendationRead(**service.serialize(item))
        for item in service.generate(user, portfolio_id, context)
    ]


@router.patch(
    "/portfolio/{portfolio_id}/recommendations/{recommendation_id}",
    response_model=RecommendationRead,
)
def update_recommendation_state(
    portfolio_id: int,
    recommendation_id: int,
    payload: ReadStateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> RecommendationRead:
    enforce_intelligence_limit(request, db, settings, user)
    service = RecommendationService(db)
    item = service.set_read(user, portfolio_id, recommendation_id, payload.is_read)
    return RecommendationRead(**service.serialize(item))


@router.get("/portfolio/{portfolio_id}/alerts", response_model=list[AlertRead])
def alerts(
    portfolio_id: int,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> list[AlertRead]:
    enforce_intelligence_limit(request, db, settings, user)
    service = RecommendationService(db)
    return [AlertRead(**service.serialize_alert(item)) for item in service.list_alerts(user, portfolio_id)]


@router.patch(
    "/portfolio/{portfolio_id}/alerts/{alert_id}",
    response_model=AlertRead,
)
def update_alert_state(
    portfolio_id: int,
    alert_id: int,
    payload: ReadStateUpdate,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> AlertRead:
    enforce_intelligence_limit(request, db, settings, user)
    service = RecommendationService(db)
    alert = service.set_alert_read(user, portfolio_id, alert_id, payload.is_read)
    return AlertRead(**service.serialize_alert(alert))


@router.post(
    "/portfolio/{portfolio_id}/stress/parse",
    response_model=StressScenarioPreview,
)
def parse_stress_scenario(
    request: Request,
    portfolio_id: int,
    payload: StressScenarioParseRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> StressScenarioPreview:
    enforce_intelligence_limit(request, db, settings, user)
    context = context_service(db, settings).build(user, portfolio_id)
    result = IntelligentStressService(db).parse(
        user,
        portfolio_id,
        payload.prompt,
        context["positions"],
    )
    return StressScenarioPreview(**result)


@router.post(
    "/portfolio/{portfolio_id}/stress/run",
    response_model=StressScenarioResultResponse,
)
def run_stress_scenario(
    request: Request,
    portfolio_id: int,
    payload: StressScenarioRunRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> StressScenarioResultResponse:
    enforce_intelligence_limit(request, db, settings, user)
    context = context_service(db, settings).build(user, portfolio_id)
    result = IntelligentStressService(db).run(
        user,
        portfolio_id,
        payload.model_dump(),
        context,
    )
    return StressScenarioResultResponse(**result)
