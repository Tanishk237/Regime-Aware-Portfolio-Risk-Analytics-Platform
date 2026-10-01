import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_database_config.py"
spec = importlib.util.spec_from_file_location("database_preflight", SCRIPT)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


@pytest.mark.parametrize("url,kind", [
    ("postgresql+psycopg://user:secret@db.example.com/db?sslmode=require", "remote"),
    ("postgresql+psycopg://user:p%40ss%23word@localhost:5432/db", "local"),
    ("postgresql+psycopg://user:secret@[::1]:5432/db", "local"),
    ("sqlite:///:memory:", "sqlite"),
])
def test_valid_urls(url, kind):
    assert preflight.validate_database_url(url, "DATABASE_URL") == kind


@pytest.mark.parametrize("url", [
    "postgresql+psycopg://user:private-secret@host:-neon-pooler-host/db",
    "postgresql+psycopg://user:private-secret@host:99999/db",
    "postgresql+psycopg://user:private-secret@host/db-${UNSET}",
    "postgresql+psycopg://user:private-secret@your-endpoint/db",
    "postgresql+psycopg://ep-example.neon.tech/db",
    "postgresql+psycopg://user:private-secret@host/",
    "",
])
def test_invalid_urls_do_not_expose_credentials(url):
    with pytest.raises(ValueError) as error:
        preflight.validate_database_url(url, "DATABASE_URL")
    assert "DATABASE_URL is invalid" in str(error.value)
    assert "private-secret" not in str(error.value)


def test_env_interpolation_overrides_and_migration_validation(tmp_path):
    config = tmp_path / ".env"
    config.write_text(
        'NEON_DATABASE_PASSWORD="private-secret"\n'
        'DATABASE_URL="postgresql+psycopg://user:${NEON_DATABASE_PASSWORD}@ep-example.neon.tech/db"\n'
        'MIGRATION_DATABASE_URL=postgresql+psycopg://user:private-secret@host:broken/db\n'
    )
    env = {key: value for key, value in os.environ.items() if key not in {
        "DATABASE_URL", "MIGRATION_DATABASE_URL", "NEON_DATABASE_PASSWORD",
    }}
    command = [sys.executable, str(SCRIPT), "--env-file", str(config)]
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "MIGRATION_DATABASE_URL is invalid" in result.stderr
    assert "private-secret" not in result.stdout + result.stderr
    result = subprocess.run(command, env={**env, "MIGRATION_DATABASE_URL": ""}, capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "remote"
