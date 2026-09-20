from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.database.models import User


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def delete_expired_guest_users(db: Session, *, retention_hours: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
    user_ids = list(
        db.scalars(
            select(User.id).where(
                User.email.like("%@guest.latent.local"),
                User.password_hash.is_(None),
                User.created_at < cutoff,
            )
        )
    )
    if not user_ids:
        return 0
    db.execute(delete(User).where(User.id.in_(user_ids)))
    db.commit()
    return len(user_ids)
