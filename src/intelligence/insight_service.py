from __future__ import annotations

from typing import Any

from src.ai.retrieval import REGIME_MODEL_DISCLOSURE
from src.api.errors import AppError


METRIC_GLOSSARY = {
    "portfolio_value": (
        "Portfolio value",
        "The latest complete market value of all open positions.",
        "It is the current capital exposed to market movements.",
        "portfolio_summary",
    ),
    "total_return": (
        "Total return",
        "Current portfolio value divided by invested capital, minus one.",
        "It shows the open portfolio's gain or loss using one consistent capital base.",
        "portfolio_summary",
    ),
    "period_return": (
        "Period return",
        "The compounded change across the portfolio return observations in the analytics window.",
        "It measures the selected historical path and can differ from the open-position return shown in the portfolio summary.",
        "risk_analytics",
    ),
    "total_pnl": (
        "Total P&L",
        "Realized profit and loss plus current unrealized profit and loss.",
        "It separates money already crystallized from changes still present in open positions.",
        "portfolio_summary",
    ),
    "cagr": (
        "CAGR",
        "The compounded annual growth rate implied by the analyzed return series.",
        "It annualizes growth, but should be read with the length of the available history.",
        "risk_analytics",
    ),
    "max_drawdown": (
        "Maximum drawdown",
        "The largest peak-to-trough decline in the analyzed portfolio return path.",
        "It describes the deepest historical loss an investor would have had to tolerate.",
        "risk_analytics",
    ),
    "annualized_volatility": (
        "Annualized volatility",
        "The annualized standard deviation of daily portfolio returns.",
        "Higher volatility means a wider range of likely outcomes, not automatically a loss.",
        "risk_analytics",
    ),
    "historical_var": (
        "Historical VaR",
        "A one-day loss threshold estimated from observed portfolio returns at the selected confidence level.",
        "VaR is a threshold, not the worst possible loss; CVaR describes losses beyond it.",
        "risk_analytics",
    ),
    "historical_cvar": (
        "Historical CVaR",
        "The average one-day loss on observations worse than historical VaR.",
        "It provides a clearer view of tail severity than VaR alone.",
        "risk_analytics",
    ),
    "sharpe": (
        "Sharpe ratio",
        "Annualized excess return divided by annualized volatility.",
        "It compares return earned with total variability taken.",
        "risk_analytics",
    ),
    "sortino": (
        "Sortino ratio",
        "Annualized excess return divided by downside deviation.",
        "It focuses on harmful volatility rather than treating upside and downside equally.",
        "risk_analytics",
    ),
    "calmar": (
        "Calmar ratio",
        "Annualized portfolio growth divided by the magnitude of maximum drawdown.",
        "It compares long-run growth with the deepest loss observed along the return path.",
        "risk_analytics",
    ),
    "parametric_var": (
        "Parametric VaR",
        "A one-day loss threshold estimated from a normal distribution fitted to portfolio returns.",
        "Comparing it with historical VaR shows how much the distribution assumption changes the loss estimate.",
        "risk_analytics",
    ),
    "parametric_cvar": (
        "Parametric CVaR",
        "The expected one-day loss beyond parametric VaR under the fitted normal distribution.",
        "It estimates tail-loss severity while relying on a stronger distribution assumption than historical CVaR.",
        "risk_analytics",
    ),
    "daily_mean_return": (
        "Daily mean return",
        "The arithmetic average of daily portfolio returns in the analyzed history.",
        "It is a small building block for annualized metrics and should not be read as a daily forecast.",
        "risk_analytics",
    ),
    "current_regime": (
        "Current regime",
        "The semantic market-state label assigned to the latest HMM hidden state.",
        "It summarizes the recent combination of return, volatility, drawdown, market, and flow features.",
        "regime_analytics",
    ),
    "regime_confidence": (
        "Regime state-fit probability",
        "The HMM probability assigned to the selected hidden state for the latest observation.",
        "A high value means the observation fits that state well; it is not a forecast certainty.",
        "regime_analytics",
    ),
}


class PortfolioInsightService:
    def explain(self, context: dict[str, Any], metric: str) -> dict[str, Any]:
        key = metric.strip().lower().replace("-", "_")
        glossary = METRIC_GLOSSARY.get(key)
        if glossary is None:
            raise AppError(
                "That metric does not have an explanation yet.",
                code="METRIC_EXPLANATION_NOT_FOUND",
                status_code=404,
            )
        title, definition, why_it_matters, source = glossary
        value = self._value(context, key)
        return {
            "metric": key,
            "title": title,
            "definition": definition,
            "value": self._format_value(key, value),
            "interpretation": self._interpret(key, value, context),
            "why_it_matters": why_it_matters,
            "source": source,
            "data_as_of": context.get("data_as_of"),
            "ask_prompt": f"Explain my {title.lower()} in context and tell me what I should review next.",
        }

    def local_answer(
        self,
        context: dict[str, Any],
        prompt: str,
        recommendations: list[dict[str, Any]],
        tools_used: list[str],
    ) -> str:
        summary_lines = context["executive_summary"]
        next_actions = [
            f"- **{item['title']}**: {item['action']} Evidence: {item['evidence']}"
            for item in recommendations[:3]
        ]
        return "\n".join(
            [
                "## Answer",
                self._answer_lead(prompt),
                "",
                "## Portfolio Snapshot",
                *[f"- {line}" for line in summary_lines],
                "",
                "## What to review next",
                *(next_actions or ["- No material rule-based risk action is active right now."]),
                "",
                "## Regime model limitation",
                REGIME_MODEL_DISCLOSURE,
                "",
                "## Data provenance",
                f"- Tools used: {', '.join(tools_used)}",
                f"- Data as of: {context.get('data_as_of') or 'latest stored valuation'}",
                "- Mode: local grounded explanation; no external LLM was called.",
            ]
        )

    def report(
        self,
        context: dict[str, Any],
        report_type: str,
        recommendations: list[dict[str, Any]],
    ) -> str:
        summary = context["summary"]
        risk = context.get("risk") or {}
        regime = context.get("regime") or {}
        metrics = risk.get("metrics", {})
        positions = context["positions"]
        base_currency = summary.get("base_currency") or ""
        return "\n".join(
            [
                f"# {report_type}",
                "",
                f"Data as of: **{context.get('data_as_of') or 'latest stored valuation'}**",
                "",
                "## Executive summary",
                *[f"- {line}" for line in context["executive_summary"]],
                "",
                "## Portfolio",
                f"- Current value: {self._format_currency(summary.get('current_value'), base_currency)}",
                f"- Invested capital: {self._format_currency(summary.get('invested_value'), base_currency)}",
                f"- Total return: {self._format_value('total_return', summary.get('total_return'))}",
                f"- Open positions: {len(positions)}",
                "",
                "## Risk",
                f"- Maximum drawdown: {self._format_value('max_drawdown', metrics.get('max_drawdown'))}",
                f"- Annualized volatility: {self._format_value('annualized_volatility', metrics.get('annualized_volatility'))}",
                f"- Historical VaR: {self._format_value('historical_var', metrics.get('historical_var'))}",
                f"- Historical CVaR: {self._format_value('historical_cvar', metrics.get('historical_cvar'))}",
                f"- Sharpe ratio: {self._format_value('sharpe', metrics.get('sharpe'))}",
                "",
                "## Regime",
                f"- Current state: {regime.get('current_regime') or 'Unavailable'}",
                f"- Model probability: {self._format_value('regime_confidence', regime.get('regime_probability'))}",
                "",
                "## Recommended actions",
                *(
                    [f"- **{item['title']}**: {item['action']} ({item['evidence']})" for item in recommendations]
                    or ["- No material rule-based recommendations are active."]
                ),
                "",
                "## Limitations",
                f"- {REGIME_MODEL_DISCLOSURE}",
                "This report is informational. Values depend on available market history and are not investment advice.",
            ]
        )

    @staticmethod
    def _value(context: dict[str, Any], key: str) -> Any:
        summary = context["summary"]
        metrics = (context.get("risk") or {}).get("metrics", {})
        regime = context.get("regime") or {}
        values = {
            "portfolio_value": summary.get("current_value"),
            "total_return": summary.get("total_return"),
            "period_return": metrics.get("period_return", metrics.get("total_return")),
            "total_pnl": summary.get("total_pnl"),
            "cagr": metrics.get("cagr"),
            "max_drawdown": metrics.get("max_drawdown"),
            "annualized_volatility": metrics.get("annualized_volatility"),
            "historical_var": metrics.get("historical_var"),
            "historical_cvar": metrics.get("historical_cvar"),
            "sharpe": metrics.get("sharpe"),
            "sortino": metrics.get("sortino"),
            "calmar": metrics.get("calmar"),
            "parametric_var": metrics.get("parametric_var"),
            "parametric_cvar": metrics.get("parametric_cvar"),
            "daily_mean_return": metrics.get("daily_mean_return"),
            "current_regime": regime.get("current_regime"),
            "regime_confidence": regime.get("regime_probability"),
        }
        return values.get(key)

    @staticmethod
    def _format_value(key: str, value: Any) -> str:
        if value is None:
            return "Unavailable"
        if key in {
            "total_return",
            "period_return",
            "cagr",
            "max_drawdown",
            "annualized_volatility",
            "historical_var",
            "historical_cvar",
            "parametric_var",
            "parametric_cvar",
            "daily_mean_return",
            "regime_confidence",
        }:
            return f"{float(value) * 100:.2f}%"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    @staticmethod
    def _format_currency(value: Any, currency: str) -> str:
        if value is None:
            return "Unavailable"
        prefix = f"{currency.strip().upper()} " if currency else ""
        return f"{prefix}{float(value):,.2f}"

    @staticmethod
    def _interpret(key: str, value: Any, context: dict[str, Any]) -> str:
        if value is None:
            return "This value is unavailable because the required valuation or market history is incomplete."
        if key == "total_return":
            return "Current value is above invested capital." if value >= 0 else "Current value is below invested capital."
        if key == "period_return":
            return "The analyzed return path gained value." if value >= 0 else "The analyzed return path lost value."
        if key == "max_drawdown":
            limit = context["risk_profile"].max_drawdown_tolerance
            return (
                "The observed drawdown is within your selected tolerance."
                if abs(value) <= limit
                else "The observed drawdown exceeds your selected tolerance."
            )
        if key == "annualized_volatility":
            return "Return variability is elevated." if value > 0.25 else "Return variability is currently contained."
        if key in {
            "historical_var",
            "historical_cvar",
            "parametric_var",
            "parametric_cvar",
        }:
            return "Read the magnitude as a potential one-day loss, not as a guaranteed outcome."
        if key in {"sharpe", "sortino", "calmar"}:
            return "Risk-adjusted performance is strong." if value >= 1 else "Risk-adjusted performance has room to improve."
        if key == "daily_mean_return":
            return "The average daily return is positive." if value >= 0 else "The average daily return is negative."
        if key == "regime_confidence":
            return "The latest observation fits this hidden state strongly." if value >= 0.75 else "The state assignment is uncertain and should be treated cautiously."
        if key == "current_regime":
            return f"The latest validated feature row is most consistent with the {value} state."
        return "Use this value alongside the portfolio's risk profile and recent market state."

    @staticmethod
    def _answer_lead(prompt: str) -> str:
        lowered = prompt.lower()
        if "regime" in lowered:
            return "The regime signal is most useful when read with its probability, duration, and current risk path."
        if "risk" in lowered or "drawdown" in lowered or "var" in lowered:
            return "Your risk should be read through drawdown, volatility, tail loss, and concentration together."
        if "capital" in lowered or "add" in lowered:
            return "Before adding capital, compare the current regime and portfolio loss profile with your stated tolerance."
        return "Here is a grounded reading of the latest portfolio analytics available to Latent."
