"""Small, allowlisted portfolio facts; no names, notes, keys or raw CSV rows."""
from __future__ import annotations

from datetime import date
import math
import re

from src.ai.safety import GroundedAnswer, GroundedPoint, render_answer, SECRET_PATTERN, EMAIL_PATTERN, INJECTION_PATTERN, UNSAFE_OUTPUT
from src.intelligence.insight_service import METRIC_GLOSSARY
from src.market.sector_taxonomy import SECTOR_ALIASES


def finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def build_evidence(context: dict, recommendations: list[dict] | None = None) -> list[dict]:
    summary = context.get("summary") or {}
    risk = context.get("risk") or {}
    metrics = risk.get("metrics") or {}
    regime = context.get("regime") or {}
    as_of = context.get("data_as_of")
    if isinstance(as_of, date):
        as_of = as_of.isoformat()
    currency = summary.get("base_currency", "")
    currency = currency if isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency) else ""
    facts = []

    def add(key, label, value, source, explanation):
        facts.append({"id": key, "label": label, "value": value, "source": source,
                      "as_of": as_of, "explanation": explanation})

    for key, label, unit in (
        ("current_value", "Value of open holdings", "money"),
        ("total_return", "Open-holding return", "percent"),
        ("total_pnl", "Total profit or loss", "money"),
    ):
        value = summary.get(key)
        if finite(value):
            display = f"{value * 100:.2f}%" if unit == "percent" else f"{currency} {value:,.2f}".strip()
            add(key, label, display, "portfolio_summary",
                "Open-holding return excludes realized gains. Total profit or loss includes realized and unrealized results.")
    for key in ("max_drawdown", "annualized_volatility", "historical_var", "historical_cvar", "sharpe"):
        value = metrics.get(key)
        if finite(value):
            definition = METRIC_GLOSSARY[key]
            add(key, definition[0], f"{value:.2f}" if key == "sharpe" else f"{value * 100:.2f}%",
                "risk_analytics", definition[1] + " " + definition[2])
    review = risk.get("review") or {}
    if finite(review.get("score")):
        add("risk_review", "Risk-review score", f"{review['score']}/100", "risk_analytics",
            "An uncalibrated summary of drawdown, volatility and risk-adjusted return, not a safety rating.")
    state = regime.get("current_regime")
    if state in {"Bull", "Bear", "Sideways", "Crisis"}:
        rule_based = (regime.get("feature_metadata") or {}).get("model_fallback_used", False)
        probability = regime.get("regime_probability")
        value = state + (" (rule-based estimate; no statistical probability)" if rule_based else " (inferred historical state)")
        if not rule_based and finite(probability) and 0 <= probability <= 1:
            value += f"; {probability * 100:.1f}% state-fit probability"
        add("market_state", "Market state", value, "regime_analytics",
            "This describes observed market conditions. It does not predict the next market move.")
    sectors = context.get("sector_allocation") or []
    sectors = [s for s in sectors if finite(s.get("weight")) and 0 <= s["weight"] <= 1]
    if sectors:
        largest = max(sectors, key=lambda s: s["weight"])
        sector = largest.get("sector", "")
        # Provider-sourced names are data, not instructions. Keep a small text surface.
        if sector in {*SECTOR_ALIASES.values(), "Other"}:
            add("sector_concentration", "Largest sector exposure", f"{sector}: {largest['weight'] * 100:.2f}%",
                "portfolio_positions", "Based on priced holdings only. Shared sector exposure can make otherwise separate holdings move together.")
    if finite(review.get("observation_count")):
        add("history_size", "Available return history", f"{int(review['observation_count'])} daily observations",
            "risk_analytics", "Short or missing history weakens estimates; more history does not guarantee a good forecast.")
    positions = sorted(
        [p for p in context.get("positions", []) if finite(p.get("market_weight")) and 0 < p["market_weight"] <= 1],
        key=lambda p: p["market_weight"], reverse=True,
    )
    for index, position in enumerate(positions[:3]):
        ticker = str(position.get("ticker") or "")
        if re.fullmatch(r"[A-Z0-9][A-Z0-9.&^-]{0,31}", ticker):
            add(f"holding_{chr(97 + index)}", f"Holding exposure: {ticker}", f"{position['market_weight'] * 100:.2f}% of priced holdings",
                "portfolio_positions", "This weight measures a holding's share of valued positions, not its share of portfolio risk.")
    profile = context.get("risk_profile")
    tolerance = getattr(profile, "max_drawdown_tolerance", None)
    if finite(tolerance) and 0 < tolerance < 1:
        add("loss_tolerance", "Your stated loss tolerance", f"{tolerance * 100:.2f}%",
            "risk_profile", "This is a preference you supplied, not a protection against losses or a validated suitability assessment.")
    for index, recommendation in enumerate((recommendations or [])[:3]):
        title = str(recommendation.get("title") or "")
        evidence = str(recommendation.get("evidence") or "")
        action = str(recommendation.get("action") or "")
        text = " ".join((title, evidence, action))
        if not title or not action or len(text) > 1000 or len(action) > 500:
            continue
        if any(pattern.search(text) for pattern in (SECRET_PATTERN, EMAIL_PATTERN, INJECTION_PATTERN, UNSAFE_OUTPUT)):
            continue
        add(f"recommendation_{chr(97 + index)}", title, evidence, "recommendations", action)
    if not facts:
        add("model_limits", "Not enough portfolio evidence", "No usable financial metrics were found.",
            "analytics_methodology", "Add trades and market history before drawing conclusions about this portfolio.")
    return facts


def data_checks(context: dict) -> list[dict]:
    positions = [p for p in context.get("positions", []) if finite(p.get("quantity")) and p["quantity"] > 0]
    unpriced = [p for p in positions if not finite(p.get("market_value"))]
    risk = context.get("risk") or {}
    regime = context.get("regime") or {}
    as_of = context.get("data_as_of")
    try:
        as_of = date.fromisoformat(str(as_of)) if as_of else None
    except ValueError:
        as_of = None
    age = (date.today() - as_of).days if as_of else None
    current = age is not None and 0 <= age <= 7
    model_available = (
        regime.get("current_regime") in {"Bull", "Bear", "Sideways", "Crisis"}
        and finite(regime.get("regime_probability"))
        and 0 <= regime["regime_probability"] <= 1
        and not (regime.get("feature_metadata") or {}).get("model_fallback_used", False)
    )
    return [
        {"label": "Holding prices", "status": "available" if positions and not unpriced else "needs_review",
         "detail": f"{len(positions) - len(unpriced)} of {len(positions)} open holdings have a stored valuation. This does not verify quote freshness.", "href": "/market"},
        {"label": "History date", "status": "available" if current else "needs_review",
         "detail": f"Latest analytics date: {as_of or 'unknown'}. Dates older than a week or in the future need review; this is not a live-feed check.", "href": "/market"},
        {"label": "Risk-review inputs", "status": "available" if (risk.get("review") or {}).get("status") == "complete" else "needs_review",
         "detail": "The review needs complete drawdown, volatility and Sharpe inputs, plus enough daily observations.", "href": "/portfolio-health"},
        {"label": "Regime method", "status": "available" if model_available else "needs_review",
         "detail": "A trained model is available; forecast accuracy is not established." if model_available else "The trained model is unavailable or a rule-based estimate is in use. No forecast confidence can be inferred.", "href": "/regime"},
    ]


def provider_context(context: dict, recommendations: list[dict] | None = None) -> dict:
    return {
        "evidence": build_evidence(context, recommendations),
        "data_quality": [{"label": c["label"], "detail": c["detail"]} for c in data_checks(context) if c["status"] == "needs_review"],
    }


def local_brief(evidence: list[dict], query: str) -> tuple[str, list[dict], dict]:
    from src.ai.retrieval import LocalContextRetriever

    result = LocalContextRetriever(top_k=5).retrieve(query, {"evidence": evidence})
    chosen = [fact for fact in evidence if f"evidence_{fact['id']}" in result.selected_sources]
    chosen = chosen[:4] or evidence[-1:]
    answer = GroundedAnswer(
        summary="A reading of the available portfolio evidence. These observations are not a forecast or an instruction to trade.",
        points=[GroundedPoint(evidence_id=f["id"], explanation=f["explanation"]) for f in chosen],
        next_step="review_recommendations" if any(f["source"] == "recommendations" for f in chosen) else (
            "review_risk" if any(f["source"] == "risk_analytics" for f in chosen) else "review_holdings"
        ),
    )
    return render_answer(answer, evidence)
