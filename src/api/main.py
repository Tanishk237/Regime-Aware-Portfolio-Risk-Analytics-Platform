from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.api.errors import register_exception_handlers
from src.api.routes import api_router
from src.config import Settings, get_settings
from src.database import get_db, init_database
from src.database.session import build_engine, build_session_factory
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
        if settings.create_db_on_startup:
            init_database(db_engine)
        yield

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
