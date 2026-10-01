"""Validate startup database URLs without connecting or printing credentials."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def validate_database_url(value: str, name: str) -> str:
    guidance = (
        f"{name} is invalid. Copy the connection URL from Neon Connect into .env "
        "(use postgresql+psycopg://). Include the user, URL-encoded password, "
        "@host and database name. Any explicit port must be numeric, normally 5432."
    )
    if not value or any(marker in value for marker in (
        "${", "replace-with", "your-endpoint", "neon-pooler-host", "neon-direct-host",
    )):
        raise ValueError(guidance)
    try:
        url = make_url(value)
        backend = url.get_backend_name()
        if backend == "sqlite":
            return "sqlite"
        if backend != "postgresql" or not url.host or not url.database:
            raise ValueError()
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError()
        if url.host.endswith(".neon.tech") and (not url.username or not url.password):
            raise ValueError()
    except Exception:
        raise ValueError(guidance) from None
    return "local" if url.host in {"localhost", "127.0.0.1", "::1"} else "remote"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env")
    args = parser.parse_args()
    values = {**dotenv_values(args.env_file), **os.environ}
    runtime = values.get("DATABASE_URL", "postgresql+psycopg://latent:latent@localhost:5432/latent")
    migration = values.get("MIGRATION_DATABASE_URL") or runtime
    try:
        kind = validate_database_url(runtime or "", "DATABASE_URL")
        validate_database_url(migration, "MIGRATION_DATABASE_URL")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        print("Credentials were not displayed. No migration was started.", file=sys.stderr)
        return 1
    print(kind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
