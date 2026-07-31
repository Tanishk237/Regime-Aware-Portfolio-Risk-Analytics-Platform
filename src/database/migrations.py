from pathlib import Path

from alembic import command
from alembic.config import Config


def build_alembic_config(
    database_url: str,
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

    return config


def run_migrations(
    database_url: str,
    revision: str = "head",
) -> None:
    command.upgrade(
        build_alembic_config(database_url),
        revision,
    )
