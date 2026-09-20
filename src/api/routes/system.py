import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.errors import AppError
from src.api.schemas import HealthResponse, ReadinessResponse, VersionResponse
from src.config import Settings, get_settings
from src.database.migrations import build_alembic_config

from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory


router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
)
def health_check(
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    return HealthResponse(
        service=settings.app_name,
        environment=settings.environment,
        database="postgresql" if settings.database_url.startswith("postgresql") else "sqlite",
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Service readiness check",
)
def readiness_check(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ReadinessResponse:
    expected_revision = ScriptDirectory.from_config(
        build_alembic_config(settings.database_url, settings.database_ssl_mode)
    ).get_current_head()
    try:
        with request.app.state.db_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            current_revision = MigrationContext.configure(connection).get_current_revision()
    except SQLAlchemyError as exc:
        raise AppError(
            "The database is unavailable.",
            code="DATABASE_UNAVAILABLE",
            status_code=503,
        ) from exc
    if current_revision != expected_revision:
        raise AppError(
            "Database migrations are not current.",
            code="DATABASE_MIGRATION_REQUIRED",
            status_code=503,
            details={"current": current_revision, "expected": expected_revision},
        )
    if settings.require_validated_regime_model:
        report_path = Path(settings.regime_validation_report_path)
        try:
            validation_report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AppError(
                "The regime validation report is unavailable.",
                code="REGIME_VALIDATION_REQUIRED",
                status_code=503,
            ) from exc
        if validation_report.get("validated") is not True:
            raise AppError(
                "The regime model has not passed the configured validation gate.",
                code="REGIME_VALIDATION_REQUIRED",
                status_code=503,
            )
    return ReadinessResponse(
        service=settings.app_name,
        database="postgresql" if settings.database_url.startswith("postgresql") else "sqlite",
        migration=current_revision or "none",
    )


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Service version",
)
def version(
    settings: Settings = Depends(get_settings),
) -> VersionResponse:
    return VersionResponse(
        service=settings.app_name,
        version=settings.app_version,
        api_prefix=settings.api_prefix,
        environment=settings.environment,
    )
