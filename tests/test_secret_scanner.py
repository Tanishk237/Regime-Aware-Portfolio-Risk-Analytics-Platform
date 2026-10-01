import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_secrets.py"
SPEC = importlib.util.spec_from_file_location("check_secrets", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
CHECK_SECRETS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK_SECRETS)
scan_text = CHECK_SECRETS.scan_text


def test_secret_scanner_allows_environment_variable_database_passwords():
    database_url = (
        "postgresql+psycopg://neondb_owner:${NEON_DATABASE_PASSWORD}"
        "@your-endpoint.neon.tech/neondb?sslmode=require"
    )

    assert scan_text(database_url) == []


def test_secret_scanner_rejects_literal_cloud_database_passwords():
    database_url = (
        "postgresql+psycopg://neondb_owner:literal-secret-value"
        "@ep-example.neon.tech/neondb?sslmode=require"
    )

    assert scan_text(database_url) == [(1, "cloud database credential")]


def test_secret_scanner_rejects_provider_tokens():
    token = "nvapi-" + ("a" * 32)

    assert scan_text(token) == [(1, "NVIDIA API key")]
