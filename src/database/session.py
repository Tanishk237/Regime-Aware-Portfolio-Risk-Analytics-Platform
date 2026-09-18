from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.database.base import Base


def build_engine(database_url: str | None = None) -> Engine:
    database_url = database_url or get_settings().database_url
    connect_args = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "", 1)
            if db_path not in (":memory:", ""):
                Path(db_path).parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )

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
