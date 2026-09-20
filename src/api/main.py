from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager
from datetime import date, timedelta
import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session

from src.api.errors import register_exception_handlers
from src.api.middleware import RequestBodyLimitMiddleware
from src.api.routes import api_router
from src.auth.lifecycle import delete_expired_guest_users
from src.auth.rate_limit import delete_expired_rate_limits
from src.config import Settings, get_settings
from src.database import get_db, init_database
from src.database.migrations import run_migrations
from src.database.session import build_engine, build_session_factory
from src.market import MarketDataService
from src.market.cache import market_data_cache
from src.market.scheduler import MarketDataRefreshScheduler
from src.utils.logging import (
    bind_request_id,
    configure_logging,
    configure_sentry,
    reset_request_id,
)
from src.utils.scheduler import BackgroundScheduler


logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(
        settings.log_level,
        json_logs=settings.log_json or settings.environment.lower() == "production",
    )
    configure_sentry(
        settings.sentry_dsn,
        environment=settings.environment,
        release=f"{settings.app_name}@{settings.app_version}",
        traces_sample_rate=settings.sentry_traces_sample_rate,
    )

    db_engine = build_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout_seconds=settings.database_pool_timeout_seconds,
        pool_recycle_seconds=settings.database_pool_recycle_seconds,
        ssl_mode=settings.database_ssl_mode,
    )
    session_factory = build_session_factory(db_engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        maintenance_scheduler = None
        if settings.run_migrations_on_startup:
            if settings.database_url in {"sqlite://", "sqlite:///:memory:"}:
                # Alembic would open a second, isolated in-memory connection.
                init_database(db_engine)
            else:
                run_migrations(
                    settings.database_url,
                    ssl_mode=settings.database_ssl_mode,
                )
        if settings.create_db_on_startup:
            init_database(db_engine)

        def run_maintenance() -> None:
            db = session_factory()
            try:
                guests_deleted = delete_expired_guest_users(
                    db,
                    retention_hours=settings.guest_data_retention_hours,
                )
                limits_deleted = delete_expired_rate_limits(db)
                if guests_deleted or limits_deleted:
                    logger.info(
                        "Lifecycle maintenance completed",
                        extra={
                            "guests_deleted": guests_deleted,
                            "rate_limits_deleted": limits_deleted,
                        },
                    )
            finally:
                db.close()

        run_maintenance()
        maintenance_scheduler = BackgroundScheduler(
            name="lifecycle-maintenance",
            interval_seconds=settings.guest_cleanup_interval_seconds,
            job=run_maintenance,
        )
        maintenance_scheduler.start()
        app.state.maintenance_scheduler = maintenance_scheduler
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
        if maintenance_scheduler is not None:
            maintenance_scheduler.stop()
        db_engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.api_docs_enabled else None,
        redoc_url="/redoc" if settings.api_docs_enabled else None,
        openapi_url="/openapi.json" if settings.api_docs_enabled else None,
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
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Server-Timing", "Retry-After"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(
        GZipMiddleware,
        minimum_size=settings.gzip_minimum_size_bytes,
        compresslevel=5,
    )
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=settings.request_body_max_bytes,
    )

    @app.middleware("http")
    async def add_performance_headers(request: Request, call_next):
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied_request_id
            if re.fullmatch(r"[A-Za-z0-9._-]{8,64}", supplied_request_id)
            else uuid4().hex
        )
        request_id_token = bind_request_id(request_id)
        started_at = perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (perf_counter() - started_at) * 1000
            response.headers["Server-Timing"] = f"app;dur={duration_ms:.2f}"
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            if request.url.path.startswith(settings.api_prefix):
                response.headers.setdefault("Cache-Control", "no-store")
            if settings.environment.lower() == "production":
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
            log_method = logger.warning if duration_ms >= settings.slow_request_threshold_ms else logger.info
            log_method(
                "HTTP request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            return response
        finally:
            reset_request_id(request_id_token)

    register_exception_handlers(app)

    app.include_router(
        api_router,
        prefix=settings.api_prefix,
    )

    return app


app = create_app()
