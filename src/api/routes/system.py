from fastapi import APIRouter, Depends

from src.api.schemas import HealthResponse, VersionResponse
from src.config import Settings, get_settings


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
