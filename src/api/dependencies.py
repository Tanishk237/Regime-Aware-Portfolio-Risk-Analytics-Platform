from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional

from src.auth import decode_access_token
from src.api.errors import AppError
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_or_create_default_user(
    db: Session,
    settings: Settings | None = None,
) -> User:
    settings = settings or get_settings()
    user = db.scalar(
        select(User).where(
            User.email == settings.default_user_email
        )
    )

    if user is not None:
        return user

    user = User(
        email=settings.default_user_email,
        full_name=settings.default_user_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    token = request.cookies.get(settings.auth_cookie_name)
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    if not token:
        raise AppError(
            "Authentication is required.",
            code="AUTH_REQUIRED",
            status_code=401,
        )

    payload = decode_access_token(
        token,
        settings.auth_secret_key,
    )
    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise AppError(
            "Could not validate authentication credentials.",
            code="INVALID_AUTH_TOKEN",
            status_code=401,
        ) from exc

    user = db.get(User, user_id)
    if user is None:
        raise AppError(
            "User not found.",
            code="USER_NOT_FOUND",
            status_code=401,
        )
    if not user.is_active:
        raise AppError(
            "This account is disabled.",
            code="USER_DISABLED",
            status_code=403,
        )

    return user
