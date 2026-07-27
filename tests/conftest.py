import os


LIVE_MARKET_TESTS = [
    "data_merger_test.py",
    "feature_builder_v2_test.py",
    "full_feature_pipeline_test.py",
    "full_ingestion_pipeline_test.py",
    "full_portfolio_pipeline_test.py",
    "full_risk_pipeline_test.py",
    "portfolio_price_test.py",
    "price_fetcher_test.py",
]


if os.getenv("RUN_LIVE_MARKET_TESTS") != "1":
    collect_ignore = LIVE_MARKET_TESTS
