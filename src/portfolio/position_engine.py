import pandas as pd


class PositionEngine:

    def build_positions(self, trades):

        rows = []

        for trade in trades:
            rows.append({
                "ticker": trade.ticker,
                "shares": trade.shares,
                "buy_price": trade.buy_price
            })

        df = pd.DataFrame(rows)
        df["weighted_cost"] = df["shares"] * df["buy_price"]

        positions = (
            df.groupby("ticker", as_index=False)
              .agg(
                  shares=("shares", "sum"),
                  total_cost=("weighted_cost", "sum")
              )
        )

        positions["avg_cost"] = positions["total_cost"] / positions["shares"]
        positions = positions.drop(columns=["total_cost"])

        return positions