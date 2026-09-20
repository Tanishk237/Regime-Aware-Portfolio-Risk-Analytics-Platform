from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.returns_repository import AnalyticsReturnsRepository
from src.analytics.utils import AnalyticsUtils
from src.database.base import Base
from src.database.models import Portfolio, PortfolioReturn, User
from src.database.session import build_engine, build_session_factory


class ReturnsRepositoryHarness(AnalyticsReturnsRepository, AnalyticsUtils):
    def __init__(self, db):
        self.db = db


def test_portfolio_return_snapshots_are_safe_under_concurrent_refresh(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'snapshots.db'}")
    Base.metadata.create_all(engine)
    session_factory = build_session_factory(engine)

    with session_factory() as db:
        user = User(email="snapshot-test@example.com", full_name="Snapshot Test")
        db.add(user)
        db.flush()
        portfolio = Portfolio(user_id=user.id, name="Snapshot Portfolio")
        db.add(portfolio)
        db.commit()
        portfolio_id = portfolio.id

    returns = pd.Series(
        [0.01, -0.02, 0.015, 0.005],
        index=pd.date_range("2025-01-01", periods=4, freq="D"),
        dtype=float,
    )

    def persist() -> None:
        with session_factory() as db:
            ReturnsRepositoryHarness(db)._persist_returns(portfolio_id, returns)

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(lambda _: persist(), range(8)))

    with session_factory() as db:
        rows = (
            db.query(PortfolioReturn)
            .filter(PortfolioReturn.portfolio_id == portfolio_id)
            .order_by(PortfolioReturn.date)
            .all()
        )
        assert len(rows) == len(returns)
        assert [row.daily_return for row in rows] == list(returns)

    engine.dispose()
