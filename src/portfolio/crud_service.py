from __future__ import annotations

from sqlalchemy import select

from src.api.errors import AppError
from src.database.models import Portfolio, User


class PortfolioCrudService:
    def list_portfolios(self, user: User) -> list[Portfolio]:
        return list(
            self.db.scalars(
                select(Portfolio)
                .where(Portfolio.user_id == user.id)
                .order_by(Portfolio.created_at.desc(), Portfolio.id.desc())
            )
        )

    def create_portfolio(
        self,
        user: User,
        *,
        name: str,
        description: str | None = None,
        base_currency: str = "INR",
        benchmark: str = "NIFTY50",
    ) -> Portfolio:
        portfolio = Portfolio(
            user_id=user.id,
            name=name.strip(),
            description=description,
            base_currency=base_currency.upper(),
            benchmark=benchmark.upper(),
        )
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)

        return portfolio

    def get_portfolio(
        self,
        user: User,
        portfolio_id: int,
    ) -> Portfolio:
        portfolio = self.db.scalar(
            select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user.id,
            )
        )

        if portfolio is None:
            raise AppError(
                "Portfolio not found.",
                code="PORTFOLIO_NOT_FOUND",
                status_code=404,
            )

        return portfolio

    def update_portfolio(
        self,
        user: User,
        portfolio_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        base_currency: str | None = None,
        benchmark: str | None = None,
        update_description: bool = False,
    ) -> Portfolio:
        portfolio = self.get_portfolio(user, portfolio_id)

        if name is not None:
            portfolio.name = name.strip()
        if update_description:
            portfolio.description = description
        if base_currency is not None:
            portfolio.base_currency = base_currency.upper()
        if benchmark is not None:
            portfolio.benchmark = benchmark.upper()

        self.db.commit()
        self.db.refresh(portfolio)

        return portfolio

    def delete_portfolio(
        self,
        user: User,
        portfolio_id: int,
    ) -> None:
        portfolio = self.get_portfolio(user, portfolio_id)
        self.db.delete(portfolio)
        self.db.commit()
