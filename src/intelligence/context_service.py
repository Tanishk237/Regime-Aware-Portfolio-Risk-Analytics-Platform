from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.analytics import AnalyticsService
from src.api.errors import AppError
from src.database.models import Portfolio, User
from src.intelligence.cache import (
    PortfolioAnalyticsCache,
    database_cache_namespace,
    portfolio_analytics_cache,
)
from src.intelligence.profile_service import RiskProfileService
from src.market import MarketDataService
from src.market.sector_taxonomy import resolve_sector
from src.portfolio.portfolio_service import PortfolioService


class PortfolioIntelligenceContextService:
    def __init__(
        self,
        db: Session,
        *,
        market_data_service: Optional[MarketDataService] = None,
        model_dir: str = "models",
        cache: Optional[PortfolioAnalyticsCache] = None,
        cache_ttl_seconds: int = 60,
        runtime_hmm_fit_enabled: bool = True,
        max_regime_observations: int = 1_500,
        max_history_days: int = 3_650,
    ):
        self.db = db
        self.market_data_service = market_data_service or MarketDataService(db)
        self.model_dir = model_dir
        self.cache = cache or portfolio_analytics_cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self.runtime_hmm_fit_enabled = runtime_hmm_fit_enabled
        self.max_regime_observations = max_regime_observations
        self.max_history_days = max_history_days

    def build(
        self,
        user: User,
        portfolio_id: int,
        *,
        refresh: bool = False,
    ) -> dict[str, Any]:
        portfolio_service = PortfolioService(
            self.db,
            market_data_service=self.market_data_service,
        )
        portfolio = portfolio_service.get_portfolio(user, portfolio_id)
        positions_models = portfolio_service.list_positions(user, portfolio.id)
        summary = portfolio_service.build_summary(
            user,
            portfolio.id,
            positions=positions_models,
        )
        summary["benchmark"] = portfolio.benchmark
        tickers = [position.ticker for position in positions_models if position.quantity > 0]
        metadata = {
            item["ticker"]: item
            for item in self.market_data_service.get_instrument_metadata(
                tickers,
                refresh=refresh,
            )
        }
        positions = [
            self._position_record(position, metadata.get(position.ticker))
            for position in positions_models
        ]
        sector_allocation = self._sector_allocation(positions)
        namespace = database_cache_namespace(self.db)
        revision = portfolio.updated_at.isoformat() if portfolio.updated_at else "initial"
        if refresh:
            self.cache.invalidate(namespace, portfolio.id)
        analytics_snapshot = self.cache.get(namespace, portfolio.id, revision)
        if analytics_snapshot is None:
            analytics_snapshot = self._build_analytics_snapshot(user, portfolio)
            self.cache.set(
                namespace,
                portfolio.id,
                revision,
                analytics_snapshot,
                self.cache_ttl_seconds,
            )
        risk = analytics_snapshot["risk"]
        regime = analytics_snapshot["regime"]
        warnings = analytics_snapshot["warnings"]
        data_as_of = analytics_snapshot["data_as_of"]
        profile = RiskProfileService(self.db).get_or_create(user)
        context = {
            "portfolio_id": portfolio.id,
            "data_as_of": data_as_of,
            "summary": summary,
            "positions": positions,
            "sector_allocation": sector_allocation,
            "risk": risk,
            "regime": regime,
            "risk_profile": profile,
            "warnings": warnings,
        }
        context["executive_summary"] = self._executive_summary(context)
        context["citations"] = self._citations(context)
        return context

    def _build_analytics_snapshot(
        self,
        user: User,
        portfolio: Portfolio,
    ) -> dict[str, Any]:
        analytics = AnalyticsService(
            self.db,
            market_data_service=self.market_data_service,
            model_dir=self.model_dir,
            runtime_hmm_fit_enabled=self.runtime_hmm_fit_enabled,
            max_regime_observations=self.max_regime_observations,
            max_history_days=self.max_history_days,
        )
        warnings: list[str] = []
        risk = self._try_analytics(
            lambda: analytics.build_risk_payload(user, portfolio.id),
            "Risk analytics are not available yet.",
            warnings,
        )
        first_trade = analytics._portfolio_first_trade_date(portfolio.id)
        regime_start = max(first_trade, date.today() - timedelta(days=365))
        regime = self._try_analytics(
            lambda: analytics.build_regime_payload(
                user,
                portfolio.id,
                start_date=regime_start,
            ),
            "Regime analytics are not available yet.",
            warnings,
        )
        data_as_of = risk.get("as_of") if risk else None
        if isinstance(data_as_of, str):
            data_as_of = date.fromisoformat(data_as_of)
        return {
            "risk": risk,
            "regime": regime,
            "warnings": warnings,
            "data_as_of": data_as_of,
        }

    def tool_results(
        self,
        context: dict[str, Any],
        prompt: str,
    ) -> tuple[list[str], dict[str, Any]]:
        text = prompt.lower()
        tools = ["get_portfolio_summary"]
        results: dict[str, Any] = {"portfolio_summary": context["summary"]}
        if any(word in text for word in ("risk", "var", "drawdown", "volatility", "sharpe", "sortino")):
            tools.append("get_risk_metrics")
            results["risk"] = context.get("risk")
        if any(word in text for word in ("regime", "state", "confidence", "transition")):
            tools.append("get_current_regime")
            results["regime"] = context.get("regime")
        if any(word in text for word in ("position", "holding", "concentration", "exposure", "ticker")):
            tools.append("get_positions")
            results["positions"] = context["positions"]
        if any(word in text for word in ("sector", "industry", "diversification", "allocation")):
            tools.append("get_sector_allocation")
            results["sector_allocation"] = context["sector_allocation"]
        if any(word in text for word in ("profile", "tolerance", "horizon", "liquidity")):
            tools.append("get_risk_profile")
            results["risk_profile"] = self._profile_record(context["risk_profile"])
        return tools, results

    @staticmethod
    def _try_analytics(callback, warning: str, warnings: list[str]) -> Optional[dict[str, Any]]:
        try:
            return callback()
        except AppError as exc:
            warnings.append(f"{warning} {exc.message}")
            return None

    @staticmethod
    def _position_record(position, metadata: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        metadata = metadata or {}
        return {
            "ticker": position.ticker,
            "quantity": position.quantity,
            "avg_cost": position.avg_cost,
            "cost_basis": position.cost_basis,
            "current_price": position.current_price,
            "market_value": position.market_value,
            "market_weight": position.market_weight,
            "unrealized_pnl": position.unrealized_pnl,
            "realized_pnl": position.realized_pnl,
            "name": metadata.get("name"),
            "sector": resolve_sector(
                position.ticker,
                metadata.get("sector"),
                metadata.get("industry"),
            ),
            "industry": metadata.get("industry"),
            "updated_at": position.updated_at,
        }

    @staticmethod
    def _sector_allocation(positions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sectors: dict[str, dict[str, Any]] = {}
        for position in positions:
            if (position.get("quantity") or 0) <= 0:
                continue
            value = position.get("market_value")
            if value is None:
                value = position.get("cost_basis")
            value = float(value or 0)
            if value <= 0:
                continue
            sector = resolve_sector(
                str(position.get("ticker") or ""),
                position.get("sector"),
                position.get("industry"),
            )
            bucket = sectors.setdefault(
                sector,
                {
                    "sector": sector,
                    "market_value": 0.0,
                    "holdings_count": 0,
                    "tickers": [],
                },
            )
            bucket["market_value"] += value
            bucket["holdings_count"] += 1
            bucket["tickers"].append(position["ticker"])

        total_value = sum(bucket["market_value"] for bucket in sectors.values())
        if total_value <= 0:
            return []
        allocation = []
        for bucket in sectors.values():
            allocation.append(
                {
                    **bucket,
                    "weight": bucket["market_value"] / total_value,
                    "tickers": sorted(bucket["tickers"]),
                }
            )
        return sorted(allocation, key=lambda item: item["market_value"], reverse=True)

    @staticmethod
    def _profile_record(profile) -> dict[str, Any]:
        return {
            "tolerance": profile.tolerance,
            "horizon_months": profile.horizon_months,
            "max_drawdown_tolerance": profile.max_drawdown_tolerance,
            "liquidity_needs": profile.liquidity_needs,
            "income_requirement": profile.income_requirement,
            "restrictions": profile.restrictions,
        }

    @staticmethod
    def _executive_summary(context: dict[str, Any]) -> list[str]:
        summary = context["summary"]
        risk = context.get("risk") or {}
        regime = context.get("regime") or {}
        metrics = risk.get("metrics", {})
        total_return = summary.get("total_return")
        max_drawdown = metrics.get("max_drawdown")
        current_regime = regime.get("current_regime")
        positions = context["positions"]
        sector_allocation = context.get("sector_allocation") or []
        largest = max(positions, key=lambda item: item.get("market_weight") or 0, default=None)
        largest_sector = sector_allocation[0] if sector_allocation else None
        lines = []
        if total_return is not None:
            direction = "up" if total_return >= 0 else "down"
            lines.append(f"The portfolio is {direction} {abs(total_return) * 100:.2f}% on invested capital.")
        if current_regime:
            confidence = regime.get("regime_probability")
            confidence_text = (
                f" at {confidence * 100:.1f}% state-fit probability"
                if confidence is not None
                else ""
            )
            lines.append(f"The current market state is {current_regime}{confidence_text}.")
        if max_drawdown is not None:
            lines.append(f"The largest observed peak-to-trough decline is {abs(max_drawdown) * 100:.2f}%.")
        if largest_sector:
            lines.append(
                f"{largest_sector['sector']} is the largest sector exposure at {largest_sector['weight'] * 100:.1f}% of current value."
            )
        if largest and largest.get("market_weight") is not None:
            lines.append(
                f"The largest holding is {largest['ticker']} at {largest['market_weight'] * 100:.1f}% of current value."
            )
        if not lines:
            lines.append("Add market history to unlock a complete portfolio intelligence summary.")
        return lines[:4]

    @staticmethod
    def _citations(context: dict[str, Any]) -> list[dict[str, Any]]:
        summary = context["summary"]
        risk = context.get("risk") or {}
        regime = context.get("regime") or {}
        as_of = context.get("data_as_of")
        citations = [
            {
                "label": "Portfolio value",
                "value": str(summary.get("current_value")),
                "source": "portfolio_summary",
                "as_of": as_of,
            },
            {
                "label": "Total return",
                "value": str(summary.get("total_return")),
                "source": "portfolio_summary",
                "as_of": as_of,
            },
        ]
        if risk:
            citations.append(
                {
                    "label": "Risk metrics",
                    "value": str(risk.get("metrics", {})),
                    "source": "risk_analytics",
                    "as_of": as_of,
                }
            )
        if regime:
            citations.append(
                {
                    "label": "Current regime",
                    "value": str(regime.get("current_regime")),
                    "source": "regime_analytics",
                    "as_of": as_of,
                }
            )
        if context.get("sector_allocation"):
            citations.append(
                {
                    "label": "Sector allocation",
                    "value": str(context["sector_allocation"]),
                    "source": "portfolio_positions",
                    "as_of": as_of,
                }
            )
        return citations
