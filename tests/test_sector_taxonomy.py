from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.market.sector_taxonomy import resolve_sector


@pytest.mark.parametrize(
    ("ticker", "expected"),
    [
        ("HDFCBANK.NS", "Financial Services"),
        ("ICICIBANK.NS", "Financial Services"),
        ("RELIANCE.NS", "Energy"),
        ("BHARTIARTL.NS", "Communication Services"),
        ("LT.NS", "Industrials"),
        ("INFY.NS", "Technology"),
        ("SBIN.NS", "Financial Services"),
        ("AXISBANK.NS", "Financial Services"),
        ("ITC.NS", "Consumer Defensive"),
        ("KOTAKBANK.NS", "Financial Services"),
        ("TCS.NS", "Technology"),
        ("SUNPHARMA.NS", "Healthcare"),
        ("M&M.NS", "Consumer Cyclical"),
        ("NTPC.NS", "Utilities"),
        ("TATASTEEL.NS", "Basic Materials"),
        ("HINDUNILVR.NS", "Consumer Defensive"),
        ("MARUTI.NS", "Consumer Cyclical"),
        ("BEL.NS", "Industrials"),
    ],
)
def test_uploaded_demo_holdings_have_local_sector_coverage(ticker, expected):
    assert resolve_sector(ticker, "Unclassified") == expected


def test_provider_sector_has_priority_and_is_normalized():
    assert resolve_sector("BEL.NS", "Consumer Staples") == "Consumer Defensive"


def test_industry_is_used_before_other_bucket():
    assert resolve_sector("NEWCO.NS", None, "Regional Banks") == "Financial Services"
    assert resolve_sector("UNKNOWN.NS") == "Other"
