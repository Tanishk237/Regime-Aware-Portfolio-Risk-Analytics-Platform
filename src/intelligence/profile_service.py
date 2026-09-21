from __future__ import annotations

from sqlalchemy.orm import Session

from src.database.models import RiskProfile, User


class RiskProfileService:
    DEFAULTS = {
        "tolerance": "moderate",
        "horizon_months": 60,
        "max_drawdown_tolerance": 0.20,
        "liquidity_needs": "medium",
        "income_requirement": None,
        "restrictions": [],
    }

    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, user: User) -> RiskProfile:
        profile = self.db.query(RiskProfile).filter(RiskProfile.user_id == user.id).one_or_none()
        if profile is not None:
            return profile
        profile = RiskProfile(user_id=user.id, **self.DEFAULTS)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update(self, user: User, **values) -> RiskProfile:
        profile = self.get_or_create(user)
        values["restrictions"] = [
            str(item).strip() for item in values.get("restrictions", []) if str(item).strip()
        ]
        for key, value in values.items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile
