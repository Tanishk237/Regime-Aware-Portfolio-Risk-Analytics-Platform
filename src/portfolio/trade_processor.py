from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    ticker: str
    shares: float
    buy_date: datetime
    buy_price: float


def create_trade(
    ticker: str,
    shares: float,
    buy_date: str,
    buy_price: float
) -> Trade:

    return Trade(
        ticker=ticker.upper(),
        shares=float(shares),
        buy_date=datetime.strptime(buy_date, "%Y-%m-%d"),
        buy_price=float(buy_price)
    )