from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        create_db_on_startup=True,
        default_user_email="test@example.com",
        default_user_name="Test User",
    )

    return TestClient(
        create_app(settings)
    )


def create_portfolio(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/portfolio",
        json={
            "name": "Core India Portfolio",
            "description": "Long-term holdings",
            "base_currency": "INR",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_portfolio_crud_flow(tmp_path):
    with build_client(tmp_path) as client:
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
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Updated Portfolio"
        assert update_response.json()["description"] is None
        assert update_response.json()["base_currency"] == "USD"

        delete_response = client.delete(f"/api/v1/portfolio/{created['id']}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/api/v1/portfolio/{created['id']}")
        assert missing_response.status_code == 404
        assert missing_response.json()["error"]["code"] == "PORTFOLIO_NOT_FOUND"


def test_manual_trade_entry_edit_delete_positions_and_summary(tmp_path):
    with build_client(tmp_path) as client:
        portfolio = create_portfolio(client)
        portfolio_id = portfolio["id"]

        first_trade = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "reliance.ns",
                "shares": 10,
                "buy_date": "2024-01-01",
                "buy_price": 2500,
            },
        )
        assert first_trade.status_code == 201
        assert first_trade.json()["ticker"] == "RELIANCE.NS"

        second_trade = client.post(
            f"/api/v1/portfolio/{portfolio_id}/trades",
            json={
                "ticker": "RELIANCE.NS",
                "shares": 5,
                "buy_date": "2024-08-01",
                "buy_price": 2900,
            },
        )
        assert second_trade.status_code == 201

        positions_response = client.get(f"/api/v1/portfolio/{portfolio_id}/positions")
        assert positions_response.status_code == 200
        positions = positions_response.json()
        assert len(positions) == 1
        assert positions[0]["ticker"] == "RELIANCE.NS"
        assert positions[0]["shares"] == 15
        assert round(positions[0]["avg_cost"], 2) == 2633.33
        assert round(positions[0]["cost_weight"], 6) == 1.0

        summary_response = client.get(f"/api/v1/portfolio/{portfolio_id}/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["trades_count"] == 2
        assert summary["positions_count"] == 1
        assert summary["invested_value"] == 39500

        trade_id = second_trade.json()["id"]
        update_trade = client.put(
            f"/api/v1/portfolio/{portfolio_id}/trades/{trade_id}",
            json={
                "shares": 10,
                "buy_price": 3000,
            },
        )
        assert update_trade.status_code == 200

        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        assert positions[0]["shares"] == 20
        assert positions[0]["cost_basis"] == 55000

        delete_trade = client.delete(
            f"/api/v1/portfolio/{portfolio_id}/trades/{trade_id}"
        )
        assert delete_trade.status_code == 204

        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        assert positions[0]["shares"] == 10
        assert positions[0]["cost_basis"] == 25000


def test_csv_upload_creates_portfolio_trades_and_positions(tmp_path):
    csv_content = (
        "ticker,shares,buy_date,buy_price,notes\n"
        "RELIANCE.NS,10,2024-01-01,2500,core\n"
        "INFY.NS,20,2024-03-15,1500,it\n"
    )

    with build_client(tmp_path) as client:
        response = client.post(
            "/api/v1/portfolio/upload",
            data={
                "name": "Uploaded Portfolio",
                "description": "CSV import",
                "base_currency": "INR",
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
        response = client.post(
            "/api/v1/portfolio/upload",
            data={"name": "Bad Upload"},
            files={
                "file": (
                    "portfolio.csv",
                    "ticker,shares\nRELIANCE.NS,10\n",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "CSV_MISSING_COLUMNS"
