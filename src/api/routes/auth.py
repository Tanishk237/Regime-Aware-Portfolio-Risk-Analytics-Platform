from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.api.errors import AppError
from src.api.schemas_auth import AuthResponse, DeleteAccountRequest, LoginRequest, SignupRequest, UserRead
from src.auth import create_access_token, hash_password, verify_password
from src.auth.lifecycle import delete_user
from src.auth.rate_limit import enforce_rate_limit, request_identity
from src.config import Settings, get_settings
from src.database import get_db
from src.database.models import User


router = APIRouter(prefix="/auth")


def _token_response(user: User, settings: Settings) -> AuthResponse:
    expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        subject=str(user.id),
        secret_key=settings.auth_secret_key,
        expires_delta=expires,
        extra_claims={"email": user.email, "ver": user.token_version},
    )
    return AuthResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
        user=UserRead.model_validate(user),
    )


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
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    enforce_rate_limit(
        db,
        bucket="auth:guest",
        identity=request_identity(request),
        limit=settings.guest_rate_limit,
        window_seconds=settings.signup_rate_limit_window_seconds,
        secret_key=settings.auth_secret_key,
    )
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
        extra_claims={"email": user.email, "guest": True, "ver": user.token_version},
    )
    return AuthResponse(
        access_token=token,
        expires_in=int(expires.total_seconds()),
        user=UserRead.model_validate(user),
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(
    payload: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    enforce_rate_limit(
        db,
        bucket="auth:signup",
        identity=request_identity(request),
        limit=settings.auth_signup_rate_limit,
        window_seconds=settings.signup_rate_limit_window_seconds,
        secret_key=settings.auth_secret_key,
    )
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
        max_age=None,
    )
    return auth


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    enforce_rate_limit(
        db,
        bucket="auth:login",
        identity=request_identity(request),
        limit=settings.auth_login_rate_limit,
        window_seconds=settings.auth_rate_limit_window_seconds,
        secret_key=settings.auth_secret_key,
    )
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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    user.token_version += 1
    db.add(user)
    db.commit()
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
    delete_user(db, user)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    payload: DeleteAccountRequest,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    if user.is_guest:
        raise AppError(
            "Guest sessions should be ended instead of deleting an account.",
            code="ACCOUNT_REQUIRED",
            status_code=400,
        )
    if not verify_password(payload.password, user.password_hash):
        raise AppError(
            "The password is incorrect.",
            code="INVALID_LOGIN",
            status_code=401,
        )
    delete_user(db, user)
    _clear_auth_cookie(response, settings)
