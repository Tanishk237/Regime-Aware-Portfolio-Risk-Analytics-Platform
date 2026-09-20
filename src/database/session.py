from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import get_settings
from src.database.base import Base


def build_engine(
    database_url: str | None = None,
    *,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout_seconds: int = 30,
    pool_recycle_seconds: int = 1800,
    ssl_mode: str = "disable",
) -> Engine:
    database_url = database_url or get_settings().database_url
    connect_args = {}
    engine_kwargs = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
    }

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_kwargs["poolclass"] = StaticPool
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "", 1)
            if db_path not in (":memory:", ""):
                Path(db_path).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

    if database_url.startswith("postgresql"):
        connect_args["sslmode"] = ssl_mode
        engine_kwargs.update(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout_seconds,
            pool_recycle=pool_recycle_seconds,
        )

    engine = create_engine(database_url, **engine_kwargs)

    if database_url.startswith("sqlite"):
        is_memory_database = database_url in {"sqlite://", "sqlite:///:memory:"}

        def configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            if not is_memory_database:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        event.listen(engine, "connect", configure_sqlite_connection)

    return engine


def build_session_factory(bind: Engine) -> sessionmaker:
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=bind,
    )


engine = build_engine()
SessionLocal = build_session_factory(engine)


def init_database(bind: Engine | None = None) -> None:
    import src.database.models  # noqa: F401

    Base.metadata.create_all(
        bind=bind or engine
    )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
