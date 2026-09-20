from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def build_alembic_config(
    database_url: str,
    ssl_mode: str | None = None,
) -> Config:
    project_root = Path(__file__).resolve().parents[2]
    config = Config(
        str(project_root / "alembic.ini")
    )
    config.set_main_option(
        "script_location",
        str(project_root / "migrations"),
    )
    config.attributes["database_url"] = database_url
    if ssl_mode is not None:
        config.attributes["database_ssl_mode"] = ssl_mode

    return config


def run_migrations(
    database_url: str,
    revision: str = "head",
    *,
    ssl_mode: str | None = None,
) -> None:
    command.upgrade(
        build_alembic_config(database_url, ssl_mode),
        revision,
    )
