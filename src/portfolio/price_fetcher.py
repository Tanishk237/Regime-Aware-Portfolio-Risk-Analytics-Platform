from src.market.providers import YahooFinanceProvider


class PriceFetcher:

    def get_current_price(
        self,
        ticker: str,
        name: bool = False
    ):
        data = YahooFinanceProvider().get_live_price(
            ticker,
            include_name=name,
        )

        if name:
            return (
                data["price"],
                data["name"],
            )

        return data["price"]
