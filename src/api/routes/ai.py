from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.ai import CopilotAIService
from src.api.dependencies import get_current_user
from src.api.errors import AppError
from src.auth.workload import enforce_workload_rate_limit
from src.api.routes.market import market_service
from src.api.schemas_ai import (
    AIProviderConfigResponse,
    AIReportRead,
    AIReportRequest,
    CopilotChatRequest,
    CopilotChatResponse,
    ProviderValidationRequest,
    ProviderValidationResponse,
)
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import AIReport, User
from src.intelligence import PortfolioInsightService, RecommendationService
from src.intelligence import PortfolioIntelligenceContextService
from src.portfolio.portfolio_service import PortfolioService


router = APIRouter(prefix="/ai")


def _enforce_ai_rate_limit(
    db: Session,
    *,
    request: Request,
    user: User,
    settings: Settings,
) -> None:
    enforce_workload_rate_limit(
        db,
        request=request,
        user=user,
        bucket="ai:generate",
        user_limit=settings.ai_rate_limit,
        guest_limit=settings.ai_guest_rate_limit,
        network_limit=settings.ai_ip_rate_limit,
        window_seconds=settings.ai_rate_limit_window_seconds,
        secret_key=settings.auth_secret_key,
    )


def _copilot_service(settings: Settings, *, timeout_seconds: float = 30.0) -> CopilotAIService:
    return CopilotAIService(
        timeout_seconds=timeout_seconds,
        nvidia_base_url=settings.nvidia_base_url,
        max_output_tokens=settings.ai_max_output_tokens,
        history_messages=settings.ai_history_messages,
        retrieval_top_k=settings.ai_retrieval_top_k,
        retrieval_character_budget=settings.ai_retrieval_character_budget,
    )


def _provider_key(provider: str, client_key: str | None, settings: Settings) -> str:
    if provider == "nvidia":
        return settings.nvidia_api_key.strip()
    return (client_key or "").strip()


def _provider_model(provider: str, requested_model: str | None, settings: Settings) -> str:
    return _provider_model_candidates(provider, requested_model, settings)[0]


def _provider_model_candidates(
    provider: str,
    requested_model: str | None,
    settings: Settings,
) -> list[str]:
    candidates: list[str] = []

    def append(model: str | None) -> None:
        normalized = (model or "").strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)

    if provider == "nvidia":
        append(settings.nvidia_model)
        for model in settings.nvidia_fallback_models:
            append(model)
    else:
        append(requested_model)
        append(CopilotAIService.DEFAULT_MODELS[provider])
        for model in CopilotAIService.FALLBACK_MODELS[provider]:
            append(model)
    return candidates


def _can_retry_with_another_model(exc: AppError) -> bool:
    details = exc.details if isinstance(exc.details, dict) else {}
    return details.get("status_code") in {400, 404, 410, 422}


async def _generate_with_model_fallback(
    *,
    settings: Settings,
    provider: str,
    api_key: str,
    prompt: str,
    context: dict,
    history: list[dict[str, str]],
    requested_model: str | None,
    timeout_seconds: float = 30.0,
) -> dict:
    models = _provider_model_candidates(provider, requested_model, settings)
    last_error: AppError | None = None
    for index, model in enumerate(models):
        try:
            return await _copilot_service(
                settings,
                timeout_seconds=timeout_seconds,
            ).generate(
                provider=provider,
                api_key=api_key,
                prompt=prompt,
                context=context,
                history=history,
                model=model,
            )
        except AppError as exc:
            last_error = exc
            if index == len(models) - 1 or not _can_retry_with_another_model(exc):
                raise
    if last_error is not None:
        raise last_error
    raise AppError(
        "No compatible model is configured for the selected AI provider.",
        code="AI_MODEL_NOT_CONFIGURED",
        status_code=503,
    )


@router.get("/provider/config", response_model=AIProviderConfigResponse)
def provider_config(
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> AIProviderConfigResponse:
    del user
    return AIProviderConfigResponse(
        default_provider="nvidia",
        managed_provider_configured=bool(settings.nvidia_api_key.strip()),
        managed_model=settings.nvidia_model,
    )


@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    request: Request,
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> CopilotChatResponse:
    _enforce_ai_rate_limit(db, request=request, user=user, settings=settings)
    builder = PortfolioIntelligenceContextService(
        db,
        market_data_service=market_service(db, settings),
        model_dir=settings.regime_model_dir,
        cache_ttl_seconds=settings.intelligence_cache_ttl_seconds,
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
        max_history_days=settings.market_data_max_history_days,
    )
    context = builder.build(user, payload.portfolio_id)
    recommendation_service = RecommendationService(db)
    recommendations = [
        recommendation_service.serialize(item)
        for item in recommendation_service.generate(user, payload.portfolio_id, context)
    ]
    tools_used, tool_results = builder.tool_results(context, payload.prompt)
    insight = PortfolioInsightService()
    local_answer = insight.local_answer(context, payload.prompt, recommendations, tools_used)
    selected_model = _provider_model(payload.provider, payload.model, settings)
    provider_key = _provider_key(payload.provider, payload.api_key, settings)
    result = {
        "provider": payload.provider,
        "model": selected_model,
        "answer": local_answer,
        "fallback_used": True,
        "response_mode": "local",
        "provider_error": None,
        "retrieval": None,
    }
    if provider_key:
        try:
            provider_result = await _generate_with_model_fallback(
                settings=settings,
                provider=payload.provider,
                api_key=provider_key,
                prompt=payload.prompt,
                context={
                    "data_as_of": context.get("data_as_of"),
                    "tool_results": tool_results,
                    "recommendations": recommendations,
                    "warnings": context.get("warnings", []),
                },
                history=[message.model_dump() for message in payload.history],
                requested_model=payload.model,
            )
            result.update(provider_result)
            result["response_mode"] = "provider"
            result["fallback_used"] = False
        except AppError as exc:
            result["response_mode"] = "local_fallback"
            result["provider_error"] = getattr(exc, "message", str(exc))
    elif payload.provider == "nvidia":
        result["response_mode"] = "local_fallback"
        result["provider_error"] = "NVIDIA AI is not configured on this server."
    return CopilotChatResponse(
        **result,
        tools_used=tools_used,
        citations=context["citations"],
        data_as_of=context.get("data_as_of"),
    )


@router.post("/provider/validate", response_model=ProviderValidationResponse)
async def validate_provider(
    request: Request,
    payload: ProviderValidationRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> ProviderValidationResponse:
    _enforce_ai_rate_limit(db, request=request, user=user, settings=settings)
    provider_key = _provider_key(payload.provider, payload.api_key, settings)
    if not provider_key:
        message = (
            "NVIDIA AI is not configured on this server."
            if payload.provider == "nvidia"
            else "A valid provider API key is required."
        )
        raise AppError(message, code="AI_API_KEY_REQUIRED", status_code=422)
    result = await _generate_with_model_fallback(
        settings=settings,
        provider=payload.provider,
        api_key=provider_key,
        prompt="Reply with the single word connected.",
        context={"purpose": "connection validation"},
        history=[],
        requested_model=payload.model,
        timeout_seconds=15,
    )
    return ProviderValidationResponse(
        provider=result["provider"],
        model=result["model"],
    )


@router.post("/reports", response_model=AIReportRead)
async def generate_report(
    request: Request,
    payload: AIReportRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> AIReportRead:
    _enforce_ai_rate_limit(db, request=request, user=user, settings=settings)
    context = PortfolioIntelligenceContextService(
        db,
        market_data_service=market_service(db, settings),
        model_dir=settings.regime_model_dir,
        cache_ttl_seconds=settings.intelligence_cache_ttl_seconds,
        runtime_hmm_fit_enabled=settings.regime_runtime_fit_enabled,
        max_regime_observations=settings.regime_max_observations,
        max_history_days=settings.market_data_max_history_days,
    ).build(user, payload.portfolio_id)
    recommendation_service = RecommendationService(db)
    recommendations = [
        recommendation_service.serialize(item)
        for item in recommendation_service.generate(user, payload.portfolio_id, context)
    ]
    insight = PortfolioInsightService()
    content = insight.report(context, payload.report_type, recommendations)
    provider = None
    model = None
    response_mode = "local"
    provider_key = _provider_key(payload.provider, payload.api_key, settings)
    if provider_key:
        try:
            generated = await _generate_with_model_fallback(
                settings=settings,
                provider=payload.provider,
                api_key=provider_key,
                prompt=(
                    f"Create a concise {payload.report_type}. Preserve every supplied number, "
                    "include data provenance, and do not provide individualized financial advice."
                ),
                context={
                    "deterministic_report": content,
                    "citations": context["citations"],
                    "warnings": context["warnings"],
                },
                history=[],
                requested_model=payload.model,
            )
            content = generated["answer"]
            provider = generated["provider"]
            model = generated["model"]
            response_mode = "provider"
        except AppError:
            response_mode = "local_fallback"
    elif payload.provider == "nvidia":
        response_mode = "local_fallback"
    report = AIReport(
        user_id=user.id,
        portfolio_id=payload.portfolio_id,
        report_type=payload.report_type,
        title=f"{payload.report_type} - {context['summary'].get('name', 'Portfolio')}",
        content=content,
        provider=provider,
        model=model,
        response_mode=response_mode,
        data_as_of=context.get("data_as_of"),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return AIReportRead(
        id=report.id,
        portfolio_id=report.portfolio_id,
        report_type=report.report_type,
        title=report.title,
        content=report.content,
        provider=report.provider,
        model=report.model,
        response_mode=response_mode,
        data_as_of=report.data_as_of,
        created_at=report.created_at or datetime.now(timezone.utc),
    )


@router.get("/reports/{portfolio_id}", response_model=list[AIReportRead])
def list_reports(
    portfolio_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AIReportRead]:
    PortfolioService(db).get_portfolio(user, portfolio_id)
    reports = (
        db.query(AIReport)
        .filter(AIReport.portfolio_id == portfolio_id, AIReport.user_id == user.id)
        .order_by(AIReport.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        AIReportRead(
            id=report.id,
            portfolio_id=report.portfolio_id,
            report_type=report.report_type,
            title=report.title,
            content=report.content,
            provider=report.provider,
            model=report.model,
            response_mode=report.response_mode,
            data_as_of=report.data_as_of,
            created_at=report.created_at,
        )
        for report in reports
    ]
