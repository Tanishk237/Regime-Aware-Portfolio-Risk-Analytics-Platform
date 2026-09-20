from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.auth.rate_limit import enforce_rate_limit, request_identity
from src.database.models import User


def enforce_workload_rate_limit(
    db: Session,
    *,
    request: Request,
    user: User,
    secret_key: str,
    bucket: str,
    user_limit: int,
    guest_limit: int,
    network_limit: int,
    window_seconds: int,
) -> None:
    enforce_rate_limit(
        db,
        bucket=f"{bucket}:user",
        identity=f"user:{user.id}",
        limit=guest_limit if user.is_guest else user_limit,
        window_seconds=window_seconds,
        secret_key=secret_key,
    )
    enforce_rate_limit(
        db,
        bucket=f"{bucket}:network",
        identity=request_identity(request),
        limit=network_limit,
        window_seconds=window_seconds,
        secret_key=secret_key,
    )
