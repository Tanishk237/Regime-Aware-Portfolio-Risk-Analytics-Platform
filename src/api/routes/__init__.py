from fastapi import APIRouter

from src.api.routes.analytics import router as analytics_router
from src.api.routes.market import router as market_router
from src.api.routes.portfolio import router as portfolio_router
from src.api.routes.system import router as system_router


api_router = APIRouter()
api_router.include_router(
    system_router,
    tags=["system"],
)
api_router.include_router(
    portfolio_router,
    tags=["portfolio"],
)
api_router.include_router(
    market_router,
    tags=["market"],
)
api_router.include_router(
    analytics_router,
    tags=["analytics"],
)
