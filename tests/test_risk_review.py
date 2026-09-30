import math

import pytest

from src.analytics.health import build_risk_review


BASE = {"max_drawdown": -.2, "annualized_volatility": .2, "sharpe": 1}


def test_review_is_explicit_and_reproducible():
    result = build_risk_review(BASE, 120)
    assert result["score"] == 75
    assert result["calculation_version"] == "risk-review-v1"
    assert 100 + sum(c["points"] for c in result["components"]) == 75
    assert "uncalibrated" in result["limitation"]


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), True, "0.2"])
@pytest.mark.parametrize("key", list(BASE))
def test_missing_or_invalid_evidence_never_becomes_a_healthy_score(key, value):
    result = build_risk_review({**BASE, key: value}, 120)
    assert result["score"] is None
    assert result["status"] == "unavailable"
    assert key in result["missing_inputs"]
    assert all(math.isfinite(c["points"]) for c in result["components"])


@pytest.mark.parametrize("count", [0, 1, 59])
def test_short_history_does_not_receive_a_score(count):
    assert build_risk_review(BASE, count)["score"] is None


def test_worsening_risk_cannot_increase_the_score():
    baseline = build_risk_review(BASE, 120)["score"]
    for key, value in [("max_drawdown", -.4), ("annualized_volatility", .5), ("sharpe", -1)]:
        assert build_risk_review({**BASE, key: value}, 120)["score"] < baseline
    assert build_risk_review({"max_drawdown": 0, "annualized_volatility": 0, "sharpe": 10}, 120)["score"] == 100
    assert build_risk_review({**BASE, "annualized_volatility": -1}, 120)["score"] is None
    assert build_risk_review({**BASE, "max_drawdown": -2}, 120)["score"] is None
