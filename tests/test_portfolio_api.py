from datetime import date
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings
from src.database.models import MarketPrice


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        run_migrations_on_startup=True,
        default_user_email="test@example.com",
        default_user_name="Test User",
    )

    return TestClient(
        create_app(settings)
    )


def authenticate(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "portfolio-test@example.com",
            "password": "strong-password",
            "full_name": "Portfolio Test User",
        },
    )
    assert response.status_code == 201
    client.headers.update(
        {"Authorization": f"Bearer {response.json()['access_token']}"}
    )


def create_portfolio(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/portfolio",
        json={
            "name": "Core India Portfolio",
            "description": "Long-term holdings",
            "base_currency": "INR",
            "benchmark": "NIFTY50",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_portfolio_crud_flow(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        created = create_portfolio(client)

        list_response = client.get("/api/v1/portfolio")
        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.json()] == [created["id"]]

        detail_response = client.get(f"/api/v1/portfolio/{created['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "Core India Portfolio"

        update_response = client.put(
            f"/api/v1/portfolio/{created['id']}",
            json={
                "name": "Updated Portfolio",
                "description": None,
                "base_currency": "usd",
                "benchmark": "niftybank",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Portfolio"
        assert update_response.json()["description"] is None
        assert update_response.json()["base_currency"] == "USD"
        assert update_response.json()["benchmark"] == "NIFTYBANK"

        delete_response = client.delete(f"/api/v1/portfolio/{created['id']}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/api/v1/portfolio/{created['id']}")
        assert missing_response.status_code == 404
        assert missing_response.json()["error"]["code"] == "PORTFOLIO_NOT_FOUND"


def test_manual_trade_entry_edit_delete_positions_and_summary(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio = create_portfolio(client)
        portfolio_id = portfolio["id"]

        first_trade = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "reliance.ns",
                "transaction_type": "BUY",
                "quantity": 10,
                "transaction_date": "2024-01-01",
                "price": 2500,
                "fees": 10,
                "taxes": 5,
            },
        )
        assert first_trade.status_code == 201
        assert first_trade.json()["ticker"] == "RELIANCE.NS"
        assert first_trade.json()["transaction_type"] == "BUY"

        second_trade = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "RELIANCE.NS",
                "transaction_type": "BUY",
                "quantity": 5,
                "transaction_date": "2024-08-01",
                "price": 2900,
            },
        )
        assert second_trade.status_code == 201

        positions_response = client.get(f"/api/v1/portfolio/{portfolio_id}/positions")
        assert positions_response.status_code == 200
        positions = positions_response.json()
        assert len(positions) == 1
        assert positions[0]["ticker"] == "RELIANCE.NS"
        assert positions[0]["quantity"] == 15
        assert round(positions[0]["avg_cost"], 2) == 2634.33
        assert round(positions[0]["cost_weight"], 6) == 1.0
        assert positions[0]["realized_pnl"] == 0

        summary_response = client.get(f"/api/v1/portfolio/{portfolio_id}/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["trades_count"] == 2
        assert summary["positions_count"] == 1
        assert summary["invested_value"] == 39515
        assert summary["realized_profit"] == 0

        trade_id = second_trade.json()["id"]
        update_trade = client.put(
            f"/api/v1/portfolio/{portfolio_id}/trades/{trade_id}",
            json={
                "quantity": 10,
                "price": 3000,
            },
        )
        assert update_trade.status_code == 200

        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        assert positions[0]["quantity"] == 20
        assert positions[0]["cost_basis"] == 55015

        delete_trade = client.delete(
            f"/api/v1/portfolio/{portfolio_id}/trades/{trade_id}"
        )
        assert delete_trade.status_code == 204

        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        assert positions[0]["quantity"] == 10
        assert positions[0]["cost_basis"] == 25015


def test_positions_and_summary_are_enriched_from_market_prices(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio = create_portfolio(client)
        portfolio_id = portfolio["id"]

        response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "RELIANCE.NS",
                "transaction_type": "BUY",
                "quantity": 10,
                "transaction_date": "2024-01-01",
                "price": 100,
            },
        )
        assert response.status_code == 201

        db = client.app.state.session_factory()
        try:
            db.add(
                MarketPrice(
                    ticker="RELIANCE.NS",
                    date=date(2024, 1, 2),
                    open=120,
                    high=121,
                    low=119,
                    close=120,
                    volume=1000,
                )
            )
            db.commit()
        finally:
            db.close()

        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        assert positions[0]["current_price"] == 120
        assert positions[0]["market_value"] == 1200
        assert positions[0]["unrealized_pnl"] == 200
        assert positions[0]["market_weight"] == 1

        summary = client.get(f"/api/v1/portfolio/{portfolio_id}/summary").json()
        assert summary["current_value"] == 1200
        assert summary["unrealized_profit"] == 200


def test_returns_endpoint_builds_missing_chart_series_from_market_prices(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio = create_portfolio(client)
        portfolio_id = portfolio["id"]

        response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "RELIANCE.NS",
                "transaction_type": "BUY",
                "quantity": 10,
                "transaction_date": "2024-01-01",
                "price": 100,
            },
        )
        assert response.status_code == 201

        db = client.app.state.session_factory()
        try:
            for day, close in (
                (date(2024, 1, 1), 100),
                (date(2024, 1, 2), 110),
                (date(2024, 1, 3), 121),
            ):
                db.add(
                    MarketPrice(
                        ticker="RELIANCE.NS",
                        date=day,
                        open=close,
                        high=close,
                        low=close,
                        close=close,
                        volume=1000,
                    )
                )
            db.commit()
        finally:
            db.close()

        returns_response = client.get(f"/api/v1/portfolio/{portfolio_id}/returns")
        assert returns_response.status_code == 200
        returns = returns_response.json()
        assert len(returns) == 2
        assert returns[0]["date"] == "2024-01-02"
        assert round(returns[0]["daily_return"], 2) == 0.1
        assert round(returns[-1]["cumulative_return"], 2) == 0.21


def test_sell_transaction_updates_quantity_and_realized_pnl(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio = create_portfolio(client)
        portfolio_id = portfolio["id"]

        client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "INFY.NS",
                "transaction_type": "BUY",
                "quantity": 20,
                "transaction_date": "2024-01-01",
                "price": 1000,
            },
        )
        sell_response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "INFY.NS",
                "transaction_type": "SELL",
                "quantity": 5,
                "transaction_date": "2024-02-01",
                "price": 1200,
                "fees": 10,
                "taxes": 5,
            },
        )
        assert sell_response.status_code == 201

        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        assert positions[0]["quantity"] == 15
        assert positions[0]["cost_basis"] == 15000
        assert positions[0]["realized_pnl"] == 985

        summary = client.get(f"/api/v1/portfolio/{portfolio_id}/summary").json()
        assert summary["realized_profit"] == 985


def test_sell_transaction_cannot_exceed_current_quantity(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio = create_portfolio(client)
        portfolio_id = portfolio["id"]

        response = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "INFY.NS",
                "transaction_type": "SELL",
                "quantity": 1,
                "transaction_date": "2024-02-01",
                "price": 1200,
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INSUFFICIENT_POSITION_QUANTITY"


def test_csv_upload_creates_portfolio_trades_and_positions(tmp_path):
    csv_content = (
        "ticker,transaction_type,quantity,transaction_date,price,broker,fees,taxes,currency,notes\n"
        "RELIANCE.NS,BUY,10,2024-01-01,2500,Zerodha,0,0,INR,core\n"
        "INFY.NS,BUY,20,2024-03-15,1500,Zerodha,0,0,INR,it\n"
    )

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload",
            data={
                "name": "Uploaded Portfolio",
                "description": "CSV import",
                "base_currency": "INR",
                "benchmark": "NIFTY50",
            },
            files={
                "file": (
                    "portfolio.csv",
                    csv_content,
                    "text/csv",
                )
            },
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["portfolio"]["name"] == "Uploaded Portfolio"
        assert payload["trades_created"] == 2
        assert len(payload["positions"]) == 2

        summary = client.get(
            f"/api/v1/portfolio/{payload['portfolio']['id']}/summary"
        ).json()
        assert summary["invested_value"] == 55000


def test_csv_upload_validates_required_columns(tmp_path):
    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload",
            data={"name": "Bad Upload"},
            files={
                "file": (
                    "portfolio.csv",
                    "ticker,quantity\nRELIANCE.NS,10\n",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "CSV_MISSING_COLUMNS"
