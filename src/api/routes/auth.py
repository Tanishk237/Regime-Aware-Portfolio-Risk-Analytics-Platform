from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.api.errors import AppError
from src.api.schemas_auth import AuthResponse, LoginRequest, SignupRequest, UserRead
from src.auth import create_access_token, hash_password, verify_password
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import (
    AIReport,
    Portfolio,
    PortfolioAlert,
    PortfolioReturn,
    Position,
    Recommendation,
    RegimePrediction,
    RiskProfile,
    RiskMetric,
    StressResult,
    Trade,
    User,
)


router = APIRouter(prefix="/auth")


def _token_response(user: User, settings: Settings) -> AuthResponse:
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.auth_secret_key,
        expires_delta=expires,
        extra_claims={"email": user.email},
    )
    return AuthResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
        user=UserRead.model_validate(user),
    )


def _delete_guest_users(db: Session, user_ids) -> None:
    portfolio_ids = select(Portfolio.id).where(Portfolio.user_id.in_(user_ids))
    for model in (
        AIReport,
        PortfolioAlert,
        Recommendation,
        RegimePrediction,
        RiskMetric,
        PortfolioReturn,
        StressResult,
        Position,
        Trade,
    ):
        db.execute(delete(model).where(model.portfolio_id.in_(portfolio_ids)))
    db.execute(delete(Portfolio).where(Portfolio.user_id.in_(user_ids)))
    db.execute(delete(RiskProfile).where(RiskProfile.user_id.in_(user_ids)))
    db.execute(delete(User).where(User.id.in_(user_ids)))
    db.commit()


def _delete_expired_guest_users(db: Session, settings: Settings) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.guest_data_retention_hours)
    guest_user_ids = select(User.id).where(
        User.email.like("%@guest.latent.local"),
        User.password_hash.is_(None),
        User.created_at < cutoff,
    )
    _delete_guest_users(db, guest_user_ids)


def _set_auth_cookie(
    response: Response,
    token: str,
    settings: Settings,
    max_age: Optional[int] = None,
) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


def _clear_auth_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_cookie_name,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


@router.post("/guest", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def guest_session(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    _delete_expired_guest_users(db, settings)
    user = User(
        email=f"guest-{secrets.token_urlsafe(18).lower()}@guest.latent.local",
        full_name="Guest",
        password_hash=None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    expires = timedelta(minutes=settings.guest_session_expire_minutes)
    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.auth_secret_key,
        expires_delta=expires,
        extra_claims={"email": user.email, "guest": True},
    )
    return AuthResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
        user=UserRead.model_validate(user),
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise AppError(
            "An account with this email already exists.",
            code="EMAIL_ALREADY_REGISTERED",
            status_code=409,
        )

    user = User(
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    auth = _token_response(user, settings)
    _set_auth_cookie(
        response,
        auth.access_token,
        settings,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return auth


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError(
            "Invalid email or password.",
            code="INVALID_LOGIN",
            status_code=401,
        )
    if not user.is_active:
        raise AppError(
            "This account is disabled.",
            code="USER_DISABLED",
            status_code=403,
        )

    auth = _token_response(user, settings)
    _set_auth_cookie(
        response,
        auth.access_token,
        settings,
        max_age=settings.access_token_expire_minutes * 60 if payload.remember_me else None,
    )
    return auth


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> None:
    _clear_auth_cookie(response, settings)


@router.delete("/guest-session", status_code=status.HTTP_204_NO_CONTENT)
def end_guest_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    if not user.is_guest:
        raise AppError(
            "Only guest sessions can be ended this way.",
            code="GUEST_SESSION_REQUIRED",
            status_code=400,
        )
    _delete_guest_users(db, [user.id])
