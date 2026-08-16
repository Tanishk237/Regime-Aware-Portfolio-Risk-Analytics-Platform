from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from src.api.errors import AppError


ALGORITHM = "HS256"
PASSWORD_ITERATIONS = 260_000


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_b64url_encode(salt)}${_b64url_encode(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False

    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        recalculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _b64url_decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_b64url_encode(recalculated), digest)
    except (TypeError, ValueError):
        return False


def create_access_token(
    *,
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        **(extra_claims or {}),
    }
    header = {"alg": ALGORITHM, "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")),
        ]
    )
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
    except ValueError as exc:
        raise _credentials_error() from exc

    signing_input = f"{header_part}.{payload_part}"
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()

    if not hmac.compare_digest(_b64url_encode(expected_signature), signature_part):
        raise _credentials_error()

    try:
        payload = json.loads(_b64url_decode(payload_part))
    except (json.JSONDecodeError, ValueError) as exc:
        raise _credentials_error() from exc

    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < int(datetime.now(timezone.utc).timestamp()):
        raise AppError(
            "Session expired. Please log in again.",
            code="TOKEN_EXPIRED",
            status_code=401,
        )

    return payload


def _credentials_error() -> AppError:
    return AppError(
        "Could not validate authentication credentials.",
        code="INVALID_AUTH_TOKEN",
        status_code=401,
    )
