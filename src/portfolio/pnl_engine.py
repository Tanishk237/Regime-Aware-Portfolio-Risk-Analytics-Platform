class PnLEngine:

    def calculate_pnl(self, positions):

        positions["cost_basis"] = (
            positions["shares"]
            *
            positions["avg_cost"]
        )

        positions["market_value"] = (
            positions["shares"]
            *
            positions["current_price"]
        )

        positions["profit"] = (
            positions["market_value"]
            -
            positions["cost_basis"]
        )

        positions["profit_pct"] = (
            positions["profit"]
            /
            positions["cost_basis"]
        ) * 100

        return positions