"""Deterministic boundaries around untrusted prompts and model output."""
from __future__ import annotations

import re
import unicodedata
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from src.api.errors import AppError


POLICY_VERSION = "grounded-readonly-v1"
MAX_PROMPT_CHARACTERS = 4000
MAX_HISTORY_CHARACTERS = 4000
MAX_RESPONSE_CHARACTERS = 10000

# These checks catch recognizable leakage, not every possible secret or injection.
SECRET_PATTERN = re.compile(
    r"(?:\b(?:nvapi-|sk-(?:proj-|ant-)?|npg_|ghp_)[A-Za-z0-9_-]{12,}"
    r"|\bAIza[A-Za-z0-9_-]{25,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?)://\S+"
    r"|\bBearer\s+[A-Za-z0-9._~-]{12,}"
    r"|\b(?:api[_ -]?key|password|secret|access[_ -]?token)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
INJECTION_PATTERN = re.compile(
    r"(?:ignore|override|disregard|bypass).{0,60}(?:instructions|rules|guardrails|system prompt)"
    r"|(?:reveal|print|show|extract).{0,60}(?:system prompt|api key|password|credentials)"
    r"|(?:execute|run).{0,30}(?:shell|sql|command|script)"
    r"|\[(?:system|developer)\]|<\|(?:im_start|system|developer)",
    re.IGNORECASE | re.DOTALL,
)
UNSAFE_OUTPUT = re.compile(
    r"https?://|www\.|javascript:|<[^>]+>|\b(?:guaranteed|risk.free|cannot lose)\b"
    r"|\b(?:buy|sell|short)\s+(?:now|immediately|all|your)\b",
    re.IGNORECASE,
)


def clean_user_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(c for c in normalized if unicodedata.category(c) != "Cf").strip()
    if SECRET_PATTERN.search(normalized):
        raise AppError(
            "Remove passwords, API keys, or connection strings from your question or recent chat. Use the connection settings for a provider key.",
            code="AI_SENSITIVE_INPUT", status_code=422,
        )
    if INJECTION_PATTERN.search(normalized):
        raise AppError(
            "Ask about this portfolio or its metrics. Copilot cannot reveal credentials, override its rules, or run commands.",
            code="AI_REQUEST_OUT_OF_SCOPE", status_code=422,
        )
    return EMAIL_PATTERN.sub("[email removed]", normalized)


def safe_history(history: list[dict[str, str]], limit: int = 6) -> list[dict[str, str]]:
    # Browser-supplied assistant messages are not evidence or trusted instructions.
    recent = [m for m in history if m.get("role") == "user"][-limit:] if limit else []
    result = []
    remaining = MAX_HISTORY_CHARACTERS
    for message in reversed(recent):
        content = clean_user_text(message.get("content", ""))
        if content and len(content) <= remaining:
            result.append({"role": "user", "content": content})
            remaining -= len(content)
    return list(reversed(result))


ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class GroundedPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: Annotated[str, StringConstraints(pattern=r"^[a-z_]+$", max_length=64)]
    explanation: ShortText


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: ShortText
    points: list[GroundedPoint] = Field(min_length=1, max_length=4)
    next_step: Literal["review_risk", "review_holdings", "check_data", "review_regime", "review_recommendations"]


NEXT_STEPS = {
    "review_recommendations": ("Review priorities", "/recommendations", "Read the evidence behind each rule-based recommendation and decide whether it fits your situation."),
    "review_risk": ("Review historical risk", "/risk", "Compare historical losses with your loss tolerance before making a decision."),
    "review_holdings": ("Review your holdings", "/portfolios", "Check whether your largest holdings and sectors match your intended diversification."),
    "check_data": ("Check market data", "/market", "Review missing or old prices before relying on the analytics."),
    "review_regime": ("Understand the market state", "/regime", "Read the model limitations alongside the current state; it is not a forecast."),
}


def validate_answer(raw: str, evidence_ids: set[str], secrets: tuple[str, ...] = ()) -> GroundedAnswer:
    try:
        if not raw or len(raw) > MAX_RESPONSE_CHARACTERS:
            raise ValueError("response size")
        if any(secret and secret in raw for secret in secrets) or SECRET_PATTERN.search(raw):
            raise ValueError("sensitive output")
        answer = GroundedAnswer.model_validate_json(raw)
        ids = [point.evidence_id for point in answer.points]
        if len(set(ids)) != len(ids) or not set(ids).issubset(evidence_ids):
            raise ValueError("unknown or duplicate evidence")
        for text in [answer.summary, *(point.explanation for point in answer.points)]:
            # Financial values are rendered from backend facts, never model prose.
            if any(c.isdigit() for c in text) or UNSAFE_OUTPUT.search(text) or EMAIL_PATTERN.search(text):
                raise ValueError("unsupported output")
        return answer
    except (ValidationError, ValueError, TypeError) as exc:
        raise AppError(
            "The AI answer did not pass the evidence checks. A local explanation is available instead.",
            code="AI_OUTPUT_REJECTED", status_code=502,
        ) from exc


def render_answer(answer: GroundedAnswer, evidence: list[dict]) -> tuple[str, list[dict], dict]:
    facts = {fact["id"]: fact for fact in evidence}
    citations = []
    lines = ["## Portfolio brief", answer.summary]
    for point in answer.points:
        fact = facts[point.evidence_id]
        lines.extend([f"### {fact['label']}", fact["value"], point.explanation])
        citations.append({key: fact[key] for key in ("label", "value", "source", "as_of")})
    title, href, description = NEXT_STEPS[answer.next_step]
    lines.extend(["### What to review next", description])
    lines.extend(["### Limitations", "Historical risk models today's holdings, not your actual trading history. A market-state probability is not forecast accuracy. AI explanations may be wrong; this is not investment advice."])
    return "\n\n".join(lines), citations, {"label": title, "href": href}
