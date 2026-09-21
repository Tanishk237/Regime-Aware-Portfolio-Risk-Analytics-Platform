from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import PortfolioAlert, Recommendation, User
from src.portfolio.portfolio_service import PortfolioService


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def generate(
        self,
        user: User,
        portfolio_id: int,
        context: dict[str, Any],
    ) -> list[Recommendation]:
        PortfolioService(self.db).get_portfolio(user, portfolio_id)
        candidates = self._build_candidates(context)
        current: list[Recommendation] = []
        for candidate in candidates:
            recommendation = (
                self.db.query(Recommendation)
                .filter(
                    Recommendation.portfolio_id == portfolio_id,
                    Recommendation.fingerprint == candidate["fingerprint"],
                )
                .one_or_none()
            )
            if recommendation is None:
                recommendation = Recommendation(
                    portfolio_id=portfolio_id,
                    date=context.get("data_as_of") or date.today(),
                    **candidate,
                )
                self.db.add(recommendation)
            else:
                recommendation.date = context.get("data_as_of") or date.today()
                for key, value in candidate.items():
                    setattr(recommendation, key, value)
            current.append(recommendation)
        self.db.commit()
        for recommendation in current:
            self.db.refresh(recommendation)
        self._sync_alerts(portfolio_id, context, current)
        return sorted(current, key=lambda item: self._severity_order(item.severity))

    def set_read(
        self,
        user: User,
        portfolio_id: int,
        recommendation_id: int,
        is_read: bool,
    ) -> Recommendation:
        PortfolioService(self.db).get_portfolio(user, portfolio_id)
        recommendation = (
            self.db.query(Recommendation)
            .filter(
                Recommendation.id == recommendation_id,
                Recommendation.portfolio_id == portfolio_id,
            )
            .one_or_none()
        )
        if recommendation is None:
            raise AppError(
                "Recommendation not found.",
                code="RECOMMENDATION_NOT_FOUND",
                status_code=404,
            )
        recommendation.is_read = is_read
        recommendation.read_at = datetime.now(timezone.utc) if is_read else None
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def list_alerts(
        self,
        user: User,
        portfolio_id: int,
    ) -> list[PortfolioAlert]:
        PortfolioService(self.db).get_portfolio(user, portfolio_id)
        return (
            self.db.query(PortfolioAlert)
            .filter(PortfolioAlert.portfolio_id == portfolio_id)
            .order_by(PortfolioAlert.is_read, PortfolioAlert.detected_at.desc())
            .all()
        )

    def set_alert_read(
        self,
        user: User,
        portfolio_id: int,
        alert_id: int,
        is_read: bool,
    ) -> PortfolioAlert:
        PortfolioService(self.db).get_portfolio(user, portfolio_id)
        alert = (
            self.db.query(PortfolioAlert)
            .filter(
                PortfolioAlert.id == alert_id,
                PortfolioAlert.portfolio_id == portfolio_id,
            )
            .one_or_none()
        )
        if alert is None:
            raise AppError("Alert not found.", code="ALERT_NOT_FOUND", status_code=404)
        alert.is_read = is_read
        alert.read_at = datetime.now(timezone.utc) if is_read else None
        self.db.commit()
        self.db.refresh(alert)
        return alert

    @staticmethod
    def serialize(recommendation: Recommendation) -> dict[str, Any]:
        return {
            "id": recommendation.id,
            "fingerprint": recommendation.fingerprint or f"recommendation-{recommendation.id}",
            "severity": recommendation.severity,
            "category": recommendation.category,
            "title": recommendation.title,
            "description": recommendation.description,
            "evidence": recommendation.evidence or "Evidence unavailable",
            "action": recommendation.action or "Review this risk driver.",
            "expected_impact": recommendation.expected_impact or "Improves risk awareness.",
            "confidence": (
                recommendation.confidence
                if recommendation.confidence is not None
                else 0.5
            ),
            "is_read": recommendation.is_read,
            "created_at": recommendation.created_at,
        }

    @staticmethod
    def serialize_alert(alert: PortfolioAlert) -> dict[str, Any]:
        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "evidence": alert.evidence,
            "is_read": alert.is_read,
            "detected_at": alert.detected_at,
        }

    def _build_candidates(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        summary = context["summary"]
        positions = context["positions"]
        risk = context.get("risk") or {}
        regime = context.get("regime") or {}
        metrics = risk.get("metrics", {})
        profile = context["risk_profile"]
        candidates: list[dict[str, Any]] = []
        max_drawdown = self._number(metrics.get("max_drawdown"))
        volatility = self._number(metrics.get("annualized_volatility"))
        cvar = self._number(metrics.get("historical_cvar"))
        sharpe = self._number(metrics.get("sharpe"))
        total_return = self._number(summary.get("total_return"))
        largest = max(positions, key=lambda item: item.get("market_weight") or 0, default=None)
        sector_allocation = context.get("sector_allocation") or []
        largest_sector = sector_allocation[0] if sector_allocation else None
        concentration = self._number(largest.get("market_weight")) if largest else None
        tolerance = profile.tolerance

        if max_drawdown is not None and abs(max_drawdown) > profile.max_drawdown_tolerance:
            candidates.append(
                self._candidate(
                    "drawdown-tolerance",
                    "high" if abs(max_drawdown) > profile.max_drawdown_tolerance * 1.35 else "medium",
                    "Risk",
                    "Drawdown exceeds your stated limit",
                    "The observed decline is larger than the loss boundary in your risk profile.",
                    f"Max drawdown {abs(max_drawdown) * 100:.2f}% vs limit {profile.max_drawdown_tolerance * 100:.2f}%",
                    "Review the positions that contributed most before adding capital.",
                    "Brings portfolio risk closer to your personal loss tolerance.",
                    0.95,
                )
            )

        volatility_limit = {"conservative": 0.16, "moderate": 0.24, "aggressive": 0.34}[tolerance]
        if volatility is not None and volatility > volatility_limit:
            candidates.append(
                self._candidate(
                    "volatility-profile",
                    "high" if volatility > volatility_limit * 1.35 else "medium",
                    "Risk",
                    "Volatility is high for your profile",
                    "Realized variability is above the range implied by your selected tolerance.",
                    f"Annualized volatility {volatility * 100:.2f}% vs profile range {volatility_limit * 100:.2f}%",
                    "Consider reducing high-volatility positions or staggering exposure changes.",
                    "May reduce day-to-day variation and downside pressure.",
                    0.90,
                )
            )

        concentration_limit = {"conservative": 0.22, "moderate": 0.30, "aggressive": 0.40}[tolerance]
        if concentration is not None and concentration > concentration_limit:
            candidates.append(
                self._candidate(
                    "top-position-concentration",
                    "high" if concentration > 0.50 else "medium",
                    "Diversification",
                    "Largest position dominates portfolio exposure",
                    "A single holding can materially determine the portfolio outcome.",
                    f"{largest['ticker']} represents {concentration * 100:.2f}% of current value",
                    "Review whether this weight is intentional and rebalance gradually if it is not.",
                    "Reduces dependence on one company-specific outcome.",
                    0.98,
                )
            )
        elif (
            concentration is not None
            and concentration >= max(0.10, concentration_limit * 0.40)
            and largest is not None
        ):
            candidates.append(
                self._candidate(
                    "top-position-monitoring",
                    "low",
                    "Diversification",
                    "Keep the largest holding under review",
                    "The largest position is meaningful even though it remains below your profile limit.",
                    f"{largest['ticker']} represents {concentration * 100:.2f}% of current value",
                    "Set a review threshold for this holding before market moves increase its weight.",
                    "Prevents gradual concentration from becoming an unintended portfolio risk.",
                    0.90,
                )
            )

        sector_limit = {"conservative": 0.35, "moderate": 0.45, "aggressive": 0.55}[tolerance]
        sector_weight = self._number(largest_sector.get("weight")) if largest_sector else None
        if sector_weight is not None and sector_weight > sector_limit:
            candidates.append(
                self._candidate(
                    f"sector-concentration-{largest_sector['sector'].lower().replace(' ', '-')}",
                    "high" if sector_weight > 0.65 else "medium",
                    "Diversification",
                    f"{largest_sector['sector']} exposure is concentrated",
                    "Several holdings can still respond to the same sector-level risk driver.",
                    f"{largest_sector['sector']} represents {sector_weight * 100:.2f}% across {largest_sector['holdings_count']} holding(s)",
                    "Review whether the shared sector exposure matches your intended diversification.",
                    "Reduces sensitivity to a single industry cycle without relying only on ticker count.",
                    0.94,
                )
            )
        elif (
            sector_weight is not None
            and sector_weight >= sector_limit * 0.55
            and largest_sector is not None
        ):
            candidates.append(
                self._candidate(
                    f"sector-monitoring-{largest_sector['sector'].lower().replace(' ', '-')}",
                    "low",
                    "Diversification",
                    f"Monitor {largest_sector['sector']} as the largest sector",
                    "This is the portfolio's largest shared economic exposure, although it is below the profile limit.",
                    f"{largest_sector['sector']} represents {sector_weight * 100:.2f}% across {largest_sector['holdings_count']} holding(s)",
                    "Track this sector weight when adding capital or rebalancing related holdings.",
                    "Keeps company-level diversification from hiding a common sector driver.",
                    0.88,
                )
            )

        if cvar is not None and abs(cvar) > 0.03:
            candidates.append(
                self._candidate(
                    "tail-loss",
                    "high" if abs(cvar) > 0.05 else "medium",
                    "Risk",
                    "Tail losses are material",
                    "Losses beyond the VaR threshold have been meaningfully larger than an ordinary down day.",
                    f"Historical CVaR {abs(cvar) * 100:.2f}%",
                    "Size positions against tail scenarios and review downside protection.",
                    "Improves resilience to unusually severe market days.",
                    0.88,
                )
            )

        regime_label = str(regime.get("current_regime") or "").lower()
        if any(word in regime_label for word in ("bear", "crisis", "volatility")):
            confidence = self._number(regime.get("regime_probability")) or 0.5
            candidates.append(
                self._candidate(
                    f"regime-{regime_label.replace(' ', '-')}",
                    "high" if "crisis" in regime_label or "bear" in regime_label else "medium",
                    "Regime",
                    f"Portfolio is operating in a {regime.get('current_regime')} state",
                    "The HMM currently detects a less supportive market environment.",
                    f"State-fit probability {confidence * 100:.2f}% (not forecast confidence)",
                    "Confirm concentration and downside limits before taking more exposure.",
                    "Aligns near-term decisions with the currently observed market state.",
                    0.65,
                )
            )
        elif regime_label:
            confidence = self._number(regime.get("regime_probability")) or 0.5
            candidates.append(
                self._candidate(
                    f"regime-monitoring-{regime_label.replace(' ', '-')}",
                    "low",
                    "Regime",
                    f"Monitor the current {regime.get('current_regime')} regime",
                    "A supportive market state can still change and does not remove portfolio-specific risk.",
                    f"State-fit probability {confidence * 100:.2f}% (not forecast confidence)",
                    "Watch for a regime transition before increasing exposure solely on recent momentum.",
                    "Keeps allocation decisions connected to changes in the observed market state.",
                    0.65,
                )
            )

        if sharpe is not None and sharpe < 0.5:
            candidates.append(
                self._candidate(
                    "weak-risk-adjusted-return",
                    "high" if sharpe < 0 else "medium",
                    "Performance",
                    "Risk-adjusted return is weak",
                    "The portfolio has not been compensated well for its observed volatility.",
                    f"Sharpe ratio {sharpe:.2f}",
                    "Review persistent underperformers and duplicated exposures.",
                    "Targets a better balance between return and variability.",
                    0.86,
                )
            )

        if total_return is not None and total_return < 0:
            severity = "high" if total_return < -0.20 else "medium" if total_return < -0.05 else "low"
            candidates.append(
                self._candidate(
                    "negative-total-return",
                    severity,
                    "Performance",
                    "Portfolio return is below invested capital",
                    "Current market value is below the capital represented by open positions.",
                    f"Total return {total_return * 100:.2f}%",
                    "Review attribution before changing the portfolio solely because of the headline return.",
                    "Encourages decisions based on drivers rather than one aggregate number.",
                    0.92,
                )
            )
        return candidates

    def _sync_alerts(
        self,
        portfolio_id: int,
        context: dict[str, Any],
        recommendations: list[Recommendation],
    ) -> None:
        alerts = []
        for recommendation in recommendations:
            if recommendation.severity not in {"high", "medium"}:
                continue
            alerts.append(
                {
                    "fingerprint": f"recommendation:{recommendation.fingerprint}",
                    "alert_type": "risk_driver",
                    "severity": recommendation.severity,
                    "title": recommendation.title,
                    "description": recommendation.description,
                    "evidence": recommendation.evidence,
                }
            )
        for warning in context.get("warnings", []):
            warning_fingerprint = hashlib.sha256(warning.encode("utf-8")).hexdigest()[:20]
            alerts.append(
                {
                    "fingerprint": f"data:{warning_fingerprint}",
                    "alert_type": "data_quality",
                    "severity": "low",
                    "title": "Analytics data needs attention",
                    "description": warning,
                    "evidence": "Generated while assembling portfolio context",
                }
            )
        for candidate in alerts:
            existing = (
                self.db.query(PortfolioAlert)
                .filter(
                    PortfolioAlert.portfolio_id == portfolio_id,
                    PortfolioAlert.fingerprint == candidate["fingerprint"],
                )
                .one_or_none()
            )
            if existing is None:
                self.db.add(PortfolioAlert(portfolio_id=portfolio_id, **candidate))
            else:
                for key, value in candidate.items():
                    setattr(existing, key, value)
        active_fingerprints = [candidate["fingerprint"] for candidate in alerts]
        stale_alerts = delete(PortfolioAlert).where(
            PortfolioAlert.portfolio_id == portfolio_id
        )
        if active_fingerprints:
            stale_alerts = stale_alerts.where(
                PortfolioAlert.fingerprint.not_in(active_fingerprints)
            )
        self.db.execute(stale_alerts)
        self.db.commit()

    @staticmethod
    def _candidate(
        fingerprint: str,
        severity: str,
        category: str,
        title: str,
        description: str,
        evidence: str,
        action: str,
        expected_impact: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "fingerprint": fingerprint,
            "severity": severity,
            "category": category,
            "title": title,
            "description": description,
            "evidence": evidence,
            "action": action,
            "expected_impact": expected_impact,
            "confidence": confidence,
        }

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            result = float(value)
            return result if result == result else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _severity_order(severity: str) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)
