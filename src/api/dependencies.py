from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import Settings, get_settings
from src.database.models import User


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
