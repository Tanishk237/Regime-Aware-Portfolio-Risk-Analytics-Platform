from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.database.models import StressResult, User
from src.portfolio.portfolio_service import PortfolioService


class IntelligentStressService:
    def __init__(self, db: Session):
        self.db = db

    def parse(
        self,
        user: User,
        portfolio_id: int,
        prompt: str,
        positions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        PortfolioService(self.db).get_portfolio(user, portfolio_id)
        market_shock = self._extract_named_percent(
            prompt,
            ("market", "nifty", "sensex", "index"),
            default=-10.0,
            minimum=-100.0,
            maximum=100.0,
        )
        volatility_shock = self._extract_named_percent(
            prompt,
            ("volatility", "vol", "vix"),
            default=25.0,
            negative_words=(),
            minimum=-100.0,
            maximum=500.0,
        )
        ticker_shocks = {}
        for position in positions:
            ticker = str(position["ticker"])
            aliases = {ticker.lower(), ticker.split(".")[0].lower()}
            value = self._extract_named_percent(
                prompt,
                tuple(aliases),
                default=None,
                minimum=-100.0,
                maximum=100.0,
            )
            if value is not None:
                ticker_shocks[ticker] = value
        assumptions = [f"Broad market shock: {market_shock:+.1f}%"]
        assumptions.append(f"Historical VaR scaled by volatility change: {volatility_shock:+.1f}%")
        assumptions.extend(
            f"{ticker} receives a specific {shock:+.1f}% shock"
            for ticker, shock in ticker_shocks.items()
        )
        if not ticker_shocks:
            assumptions.append("All positions receive the broad market shock.")
        return {
            "name": "AI-assisted stress scenario",
            "prompt": prompt,
            "market_shock": market_shock,
            "volatility_shock": volatility_shock,
            "ticker_shocks": ticker_shocks,
            "assumptions": assumptions,
            "requires_confirmation": True,
        }

    def run(
        self,
        user: User,
        portfolio_id: int,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        PortfolioService(self.db).get_portfolio(user, portfolio_id)
        if not payload.get("confirmed"):
            raise AppError(
                "Confirm the parsed scenario before running it.",
                code="STRESS_CONFIRMATION_REQUIRED",
                status_code=409,
            )
        summary = context["summary"]
        value_before = summary.get("current_value")
        if value_before is None or value_before <= 0:
            raise AppError(
                "A complete current portfolio value is required for stress testing.",
                code="STRESS_VALUE_UNAVAILABLE",
                status_code=409,
            )
        ticker_shocks = {
            str(key).upper(): float(value)
            for key, value in payload.get("ticker_shocks", {}).items()
        }
        position_impacts = []
        for position in context["positions"]:
            before = position.get("market_value")
            if before is None:
                raise AppError(
                    "Every open position needs a market value before running a stress scenario.",
                    code="STRESS_POSITION_VALUE_UNAVAILABLE",
                    status_code=409,
                )
            ticker = str(position["ticker"])
            shock = ticker_shocks.get(ticker, float(payload["market_shock"]))
            after = max(float(before) * (1 + shock / 100), 0.0)
            position_impacts.append(
                {
                    "ticker": ticker,
                    "applied_shock": shock,
                    "value_before": float(before),
                    "value_after": after,
                    "impact": after - float(before),
                }
            )
        value_after = sum(item["value_after"] for item in position_impacts)
        risk_metrics = (context.get("risk") or {}).get("metrics", {})
        var_before = self._number(risk_metrics.get("historical_var"))
        var_after = (
            var_before * (1 + float(payload.get("volatility_shock", 0)) / 100)
            if var_before is not None
            else None
        )
        assumptions = [f"Broad market shock: {float(payload['market_shock']):+.1f}%"]
        assumptions.extend(
            f"{ticker}: {shock:+.1f}%" for ticker, shock in ticker_shocks.items()
        )
        result = StressResult(
            portfolio_id=portfolio_id,
            scenario_name=payload["name"],
            scenario_parameters={
                "description": payload.get("description"),
                "market_shock": payload["market_shock"],
                "volatility_shock": payload.get("volatility_shock", 0),
                "ticker_shocks": ticker_shocks,
                "position_impacts": position_impacts,
                "assumptions": assumptions,
            },
            portfolio_value_before=value_before,
            portfolio_value_after=value_after,
            risk_before={"historical_var": var_before},
            risk_after={"historical_var": var_after},
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return {
            "id": result.id,
            "name": result.scenario_name,
            "description": payload.get("description"),
            "value_before": float(value_before),
            "value_after": value_after,
            "estimated_impact": value_after - float(value_before),
            "estimated_impact_pct": (value_after - float(value_before)) / float(value_before),
            "historical_var_before": var_before,
            "historical_var_after": var_after,
            "position_impacts": position_impacts,
            "assumptions": assumptions,
            "generated_at": result.created_at or datetime.now(timezone.utc),
        }

    @classmethod
    def _extract_named_percent(
        cls,
        prompt: str,
        names: tuple[str, ...],
        *,
        default: float | None,
        negative_words: tuple[str, ...] = ("fall", "falls", "drop", "drops", "decline", "down", "crash", "lose", "loses"),
        minimum: float = -100.0,
        maximum: float = 500.0,
    ) -> float | None:
        lowered = prompt.lower()
        for name in sorted(names, key=len, reverse=True):
            escaped = re.escape(name)
            patterns = (
                rf"{escaped}[^%]{{0,45}}?(-?\d+(?:\.\d+)?)\s*%",
                rf"(-?\d+(?:\.\d+)?)\s*%[^.\n]{{0,45}}?{escaped}",
            )
            for pattern in patterns:
                match = re.search(pattern, lowered)
                if not match:
                    continue
                value = float(match.group(1))
                segment = lowered[max(0, match.start() - 30): match.end() + 30]
                if value > 0 and negative_words and any(word in segment for word in negative_words):
                    value = -value
                return max(minimum, min(maximum, value))
        return default

    @staticmethod
    def _number(value: Any) -> float | None:
        try:
            result = float(value)
            return result if result == result else None
        except (TypeError, ValueError):
            return None
