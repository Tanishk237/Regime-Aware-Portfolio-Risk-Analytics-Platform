from __future__ import annotations

from typing import Optional


UNRESOLVED_SECTORS = {"", "n/a", "na", "none", "unknown", "unclassified"}

# Stable local coverage for the Indian large-cap universe used by Latent's demo
# and common portfolio imports. Provider metadata remains the primary source.
INDIAN_EQUITY_SECTORS = {
    "AXISBANK": "Financial Services",
    "BEL": "Industrials",
    "BHARTIARTL": "Communication Services",
    "HDFCBANK": "Financial Services",
    "HINDUNILVR": "Consumer Defensive",
    "ICICIBANK": "Financial Services",
    "INFY": "Technology",
    "ITC": "Consumer Defensive",
    "KOTAKBANK": "Financial Services",
    "LT": "Industrials",
    "M&M": "Consumer Cyclical",
    "MARUTI": "Consumer Cyclical",
    "NTPC": "Utilities",
    "RELIANCE": "Energy",
    "SBIN": "Financial Services",
    "SUNPHARMA": "Healthcare",
    "TATASTEEL": "Basic Materials",
    "TCS": "Technology",
}

SECTOR_ALIASES = {
    "basic materials": "Basic Materials",
    "communication services": "Communication Services",
    "consumer cyclical": "Consumer Cyclical",
    "consumer defensive": "Consumer Defensive",
    "consumer discretionary": "Consumer Cyclical",
    "consumer staples": "Consumer Defensive",
    "energy": "Energy",
    "financial": "Financial Services",
    "financial services": "Financial Services",
    "healthcare": "Healthcare",
    "industrial": "Industrials",
    "industrials": "Industrials",
    "real estate": "Real Estate",
    "technology": "Technology",
    "utilities": "Utilities",
}

INDUSTRY_SECTOR_RULES = (
    (
        ("bank", "insurance", "asset management", "credit service", "capital market"),
        "Financial Services",
    ),
    (
        ("software", "information technology", "semiconductor", "computer hardware"),
        "Technology",
    ),
    (("telecom", "communication", "internet content"), "Communication Services"),
    (("pharma", "biotech", "medical", "health"), "Healthcare"),
    (("oil", "gas", "energy", "refin"), "Energy"),
    (("steel", "metal", "mining", "chemical", "material"), "Basic Materials"),
    (("utility", "electric", "power generation"), "Utilities"),
    (
        ("aerospace", "defense", "engineering", "construction", "industrial"),
        "Industrials",
    ),
    (
        ("auto", "vehicle", "consumer durables", "apparel", "restaurant"),
        "Consumer Cyclical",
    ),
    (
        ("tobacco", "household", "packaged food", "beverage", "personal product"),
        "Consumer Defensive",
    ),
    (("real estate", "reit"), "Real Estate"),
)


def resolve_sector(
    ticker: str,
    sector: Optional[str] = None,
    industry: Optional[str] = None,
) -> str:
    provider_sector = str(sector or "").strip()
    if provider_sector.lower() not in UNRESOLVED_SECTORS:
        return SECTOR_ALIASES.get(provider_sector.lower(), provider_sector)

    symbol = ticker.strip().upper().split(".", maxsplit=1)[0]
    if symbol in INDIAN_EQUITY_SECTORS:
        return INDIAN_EQUITY_SECTORS[symbol]

    normalized_industry = str(industry or "").strip().lower()
    for keywords, resolved_sector in INDUSTRY_SECTOR_RULES:
        if any(keyword in normalized_industry for keyword in keywords):
            return resolved_sector

    return "Other"
