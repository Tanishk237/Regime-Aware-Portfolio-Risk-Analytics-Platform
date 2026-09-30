"""One transparent, uncalibrated risk-review indicator for every consumer."""
from __future__ import annotations

import math
from numbers import Real


MIN_REVIEW_OBSERVATIONS = 60
REVIEW_VERSION = "risk-review-v1"


def build_risk_review(metrics: dict, observation_count: int) -> dict:
    values = {}
    for key in ("max_drawdown", "annualized_volatility", "sharpe"):
        value = metrics.get(key)
        values[key] = (
            float(value)
            if isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
            else None
        )
    if values["annualized_volatility"] is not None and values["annualized_volatility"] < 0:
        values["annualized_volatility"] = None
    if values["max_drawdown"] is not None and not -1 <= values["max_drawdown"] <= 0:
        values["max_drawdown"] = None
    missing = [key for key, value in values.items() if value is None]
    if observation_count < MIN_REVIEW_OBSERVATIONS:
        missing.append(f"At least {MIN_REVIEW_OBSERVATIONS} daily returns")

    components = []
    if values["max_drawdown"] is not None:
        components.append({
            "key": "drawdown", "label": "Largest historical fall",
            "value": values["max_drawdown"],
            "points": -min(abs(values["max_drawdown"]) * 100, 40),
            "rule": "Subtract one point per percentage point of drawdown, up to 40.",
        })
    if values["annualized_volatility"] is not None:
        components.append({
            "key": "volatility", "label": "Return variability",
            "value": values["annualized_volatility"],
            "points": -min(values["annualized_volatility"] * 50, 30),
            "rule": "Subtract half a point per percentage point of annual volatility, up to 30.",
        })
    if values["sharpe"] is not None:
        components.append({
            "key": "sharpe", "label": "Return relative to risk",
            "value": values["sharpe"],
            "points": max(-10, min(values["sharpe"] * 5, 10)),
            "rule": "Add five times the Sharpe ratio, limited to minus or plus 10 points.",
        })
    score = None if missing else round(max(0, min(100, 100 + sum(c["points"] for c in components))))
    return {
        "score": score,
        "status": "unavailable" if missing else "complete",
        "category": "Not enough evidence" if score is None else (
            "Lower historical concern" if score >= 80 else "Review risk" if score >= 60 else "Elevated historical concern"
        ),
        "calculation_version": REVIEW_VERSION,
        "observation_count": observation_count,
        "minimum_observations": MIN_REVIEW_OBSERVATIONS,
        "missing_inputs": missing,
        "components": components,
        "limitation": (
            "An uncalibrated review aid for a hypothetical basket of today's holdings, not a forecast or investment rating. "
            "Higher means less historical risk under this formula. Sector concentration, price freshness, "
            "and your personal needs must be reviewed separately."
        ),
    }
