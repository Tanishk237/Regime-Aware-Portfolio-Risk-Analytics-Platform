from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.api.errors import register_exception_handlers
from src.api.routes import api_router
from src.config import Settings, get_settings
from src.database import get_db, init_database
from src.database.migrations import run_migrations
from src.database.session import build_engine, build_session_factory
from src.market import MarketDataService
from src.market.cache import market_data_cache
from src.market.scheduler import MarketDataRefreshScheduler
from src.utils.logging import configure_logging


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    db_engine = build_engine(settings.database_url)
    session_factory = build_session_factory(db_engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        if settings.run_migrations_on_startup:
            run_migrations(settings.database_url)
        if settings.create_db_on_startup:
            init_database(db_engine)
        if settings.market_data_refresh_enabled and settings.market_data_refresh_symbols:
            def refresh_market_data() -> None:
                db = session_factory()
                try:
                    MarketDataService(
                        db,
                        default_fii_dii_path=settings.fii_dii_csv_path,
                        provider_name=settings.market_data_provider,
                        cache=market_data_cache,
                        cache_ttl_seconds=settings.market_data_cache_ttl_seconds,
                        provider_retries=settings.market_data_provider_retries,
                        provider_retry_backoff_seconds=settings.market_data_provider_retry_backoff_seconds,
                    ).get_historical_prices(
                        settings.market_data_refresh_symbols,
                        date.today() - timedelta(days=30),
                        date.today(),
                    )
                finally:
                    db.close()

            scheduler = MarketDataRefreshScheduler(
                refresh_interval_seconds=settings.market_data_refresh_interval_seconds,
                refresh_job=refresh_market_data,
            )
            scheduler.start()
            app.state.market_data_scheduler = scheduler
        yield
        if scheduler is not None:
            scheduler.stop()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.db_engine = db_engine
    app.state.session_factory = session_factory
    app.dependency_overrides[get_settings] = lambda: settings

    def app_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = app_get_db

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(
        api_router,
        prefix=settings.api_prefix,
    )

    return app


app = create_app()
