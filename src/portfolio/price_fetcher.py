import yfinance as yf


class PriceFetcher:

    def get_current_price(
        self,
        ticker: str,
        name: bool = False
    ):
        data = yf.Ticker(ticker)

        price = float(
            data.history(period="1d")["Close"].iloc[-1]
        )

        if name:
            return (
                price,
                data.info.get("longName", "Unknown")
            )

        return price