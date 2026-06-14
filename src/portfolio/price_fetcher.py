import yfinance as yf


class PriceFetcher:

    def get_current_price(self, ticker: str) -> float:

        data = yf.Ticker(ticker)
        
        return float(
            data.history(period="1d")["Close"].iloc[-1]
        )