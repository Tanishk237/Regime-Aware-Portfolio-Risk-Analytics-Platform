from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import RateLimitWindow


def request_identity(request: Request) -> str:
    client = request.client
    return client.host if client is not None and client.host else "unknown"


def _identity_hash(identity: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"),
        identity.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _window_bounds(now: datetime, window_seconds: int) -> tuple[datetime, datetime]:
    epoch = int(now.timestamp())
    start_epoch = epoch - (epoch % window_seconds)
    start = datetime.fromtimestamp(start_epoch, tz=timezone.utc)
    return start, start + timedelta(seconds=window_seconds)


def enforce_rate_limit(
    db: Session,
    *,
    bucket: str,
    identity: str,
    limit: int,
    window_seconds: int,
    secret_key: str,
) -> None:
    now = datetime.now(timezone.utc)
    window_start, expires_at = _window_bounds(now, window_seconds)
    hashed_identity = _identity_hash(identity, secret_key)

    for attempt in range(2):
        window = db.scalar(
            select(RateLimitWindow)
            .where(
                RateLimitWindow.bucket == bucket,
                RateLimitWindow.identity_hash == hashed_identity,
                RateLimitWindow.window_start == window_start,
            )
            .with_for_update()
        )
        if window is None:
            window = RateLimitWindow(
                bucket=bucket,
                identity_hash=hashed_identity,
                window_start=window_start,
                request_count=1,
                expires_at=expires_at,
            )
            db.add(window)
            try:
                db.commit()
                return
            except IntegrityError:
                db.rollback()
                if attempt == 0:
                    continue
                raise

        if window.request_count >= limit:
            db.rollback()
            retry_after = max(1, int((expires_at - now).total_seconds()))
            raise AppError(
                "Too many requests. Please wait before trying again.",
                code="RATE_LIMITED",
                status_code=429,
                details={"retry_after_seconds": retry_after, "bucket": bucket},
                headers={"Retry-After": str(retry_after)},
            )

        window.request_count += 1
        db.commit()
        return


def delete_expired_rate_limits(db: Session) -> int:
    result = db.execute(
        delete(RateLimitWindow).where(
            RateLimitWindow.expires_at < datetime.now(timezone.utc)
        )
    )
    db.commit()
    return int(result.rowcount or 0)
