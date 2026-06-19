import yfinance as yf


def get_price_history(
    tickers,
    start_date
):

    data = yf.download(
        tickers,
        start=start_date,
        auto_adjust=True,
        progress=False
    )

    return data["Close"]