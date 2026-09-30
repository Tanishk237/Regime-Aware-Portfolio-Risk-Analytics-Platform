from src.api.errors import AppError


def validate_trade_currency(base_currency: str, currency: str, ticker: str) -> None:
    base = base_currency.strip().upper()
    trade_currency = currency.strip().upper()
    if trade_currency != base:
        raise AppError(
            f"This portfolio uses {base}; {ticker} is recorded in {trade_currency}. Use a separate portfolio for each currency. FX conversion is not supported.",
            code="PORTFOLIO_CURRENCY_MISMATCH", status_code=422,
        )
    if ticker.upper().endswith((".NS", ".BO")) and base != "INR":
        raise AppError(
            "NSE and BSE share prices are in INR. Use an INR portfolio for these symbols.",
            code="INSTRUMENT_CURRENCY_MISMATCH", status_code=422,
        )
