from datetime import date
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings
from src.database.models import MarketPrice, PortfolioReturn
from src.market import MarketDataService


def build_client(
    tmp_path,
    *,
    csv_upload_max_bytes: int = 5 * 1024 * 1024,
    **settings_overrides,
) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        run_migrations_on_startup=True,
        default_user_email="test@example.com",
        default_user_name="Test User",
        csv_upload_max_bytes=csv_upload_max_bytes,
        **settings_overrides,
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
        assert summary["unrealized_pnl"] == 200
        assert summary["unrealized_profit"] == 200
        assert summary["realized_pnl"] == 0
        assert summary["total_pnl"] == 200
        assert summary["return_pct"] == 0.2
        assert summary["unrealized_profit_pct"] == 0.2
        assert summary["total_return"] == 0.2


def test_summary_total_return_uses_current_value_over_invested_value(tmp_path):
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
                    open=87,
                    high=88,
                    low=86,
                    close=87,
                    volume=1000,
                )
            )
            db.add(
                PortfolioReturn(
                    portfolio_id=portfolio_id,
                    date=date(2024, 1, 2),
                    daily_return=-0.10,
                    cumulative_return=-0.10,
                    portfolio_value=0.90,
                )
            )
            db.commit()
        finally:
            db.close()

        summary = client.get(f"/api/v1/portfolio/{portfolio_id}/summary").json()
        assert summary["current_value"] == 870
        assert summary["unrealized_pnl"] == -130
        assert summary["total_pnl"] == -130
        assert summary["return_pct"] == -0.13
        assert summary["unrealized_profit_pct"] == -0.13
        assert summary["total_return"] == -0.13


def test_summary_does_not_publish_partial_portfolio_valuation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        MarketDataService,
        "get_historical_prices",
        lambda self, tickers, start_date, end_date, persist=True: [],
    )

    with build_client(tmp_path) as client:
        authenticate(client)
        portfolio_id = create_portfolio(client)["id"]

        for ticker in ("RELIANCE.NS", "TCS.NS"):
            response = client.post(
                f"/api/v1/portfolio/{portfolio_id}/trades",
                json={
                    "ticker": ticker,
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

        summary = client.get(f"/api/v1/portfolio/{portfolio_id}/summary").json()

        assert summary["invested_value"] == 2000
        assert summary["current_value"] is None
        assert summary["unrealized_pnl"] is None
        assert summary["total_pnl"] is None
        assert summary["return_pct"] is None
        assert summary["total_return"] is None


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


def test_csv_preview_maps_common_broker_columns_and_normalizes_rows(tmp_path):
    csv_content = (
        "Symbol,Side,Qty,Trade Date,Execution Price,Brokerage\n"
        "reliance.ns,buy,10,2026-01-05,2500,12.5\n"
        "reliance.ns,sell,2,2026-02-05,2700,8\n"
    )

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload/preview",
            files={"file": ("broker-export.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["valid"] is True
        assert payload["total_rows"] == 2
        assert payload["valid_rows"] == 2
        assert payload["column_mapping"]["Symbol"] == "ticker"
        assert payload["column_mapping"]["Execution Price"] == "price"
        assert payload["preview"][0]["ticker"] == "RELIANCE.NS"
        assert payload["preview"][0]["transaction_type"] == "BUY"


def test_csv_preview_accepts_valid_nse_tickers_with_ampersands(tmp_path):
    csv_content = (
        "ticker,transaction_type,quantity,transaction_date,price\n"
        "M&M.NS,BUY,10,2026-04-08,2950\n"
    )

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload/preview",
            files={"file": ("nse-ticker.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["valid"] is True
        assert payload["preview"][0]["ticker"] == "M&M.NS"


def test_csv_resolver_repairs_safe_broker_formatting_and_revalidates(tmp_path):
    csv_content = (
        "Symbol,Side,Qty,Trade Date,Execution Price,Currency\n"
        '" nse:reliance ",purchase,"1,000",18/08/2026,"₹2,450.50", inr\n'
    )

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload/resolve",
            files={"file": ("repairable.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["report"]["valid"] is True
        assert payload["report"]["preview"][0] == {
            "ticker": "RELIANCE.NS",
            "transaction_type": "BUY",
            "quantity": 1000.0,
            "transaction_date": "2026-08-18",
            "price": 2450.5,
            "currency": "INR",
            "fees": 0.0,
            "taxes": 0.0,
        }
        assert {change["field"] for change in payload["changes"]} >= {
            "ticker",
            "transaction_type",
            "quantity",
            "transaction_date",
            "price",
            "currency",
        }
        assert "RELIANCE.NS" in payload["resolved_csv"]


def test_csv_preview_reports_actionable_row_errors_without_importing(tmp_path):
    csv_content = (
        "ticker,transaction_type,quantity,transaction_date,price\n"
        "INFY.NS,SELL,5,not-a-date,-100\n"
    )

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload/preview",
            files={"file": ("invalid.csv", csv_content, "text/csv")},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["valid"] is False
        assert payload["valid_rows"] == 0
        assert {item["field"] for item in payload["errors"]} >= {
            "quantity",
            "price",
            "transaction_date",
        }
        assert client.get("/api/v1/portfolio").json() == []


def test_repository_sample_csv_completes_the_portfolio_import_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(
        MarketDataService,
        "get_historical_prices",
        lambda self, tickers, start_date, end_date, persist=True: [],
    )
    sample_path = Path(__file__).resolve().parents[1] / "testing" / "sample_portfolio_trades.csv"

    with build_client(tmp_path) as client:
        authenticate(client)
        response = client.post(
            "/api/v1/portfolio/upload",
            data={
                "name": "Sample portfolio trades",
                "description": "Repository end-to-end fixture",
                "base_currency": "INR",
                "benchmark": "NIFTY50",
            },
            files={"file": (sample_path.name, sample_path.read_bytes(), "text/csv")},
        )

        assert response.status_code == 201
        payload = response.json()
        portfolio_id = payload["portfolio"]["id"]
        assert payload["trades_created"] == 10
        assert len(payload["positions"]) == 7

        trades = client.get(f"/api/v1/portfolio/{portfolio_id}/trades").json()
        positions = client.get(f"/api/v1/portfolio/{portfolio_id}/positions").json()
        summary = client.get(f"/api/v1/portfolio/{portfolio_id}/summary").json()

        assert len(trades) == 10
        assert len(positions) == 7
        assert summary["trades_count"] == 10
        assert summary["positions_count"] == 7
        assert summary["invested_value"] > 0


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


def test_csv_upload_rejects_empty_invalid_encoding_and_oversized_files(tmp_path):
    with build_client(tmp_path, csv_upload_max_bytes=32) as client:
        authenticate(client)

        empty = client.post(
            "/api/v1/portfolio/upload",
            data={"name": "Empty Upload"},
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert empty.status_code == 400
        assert empty.json()["error"]["code"] == "CSV_EMPTY"

        invalid_encoding = client.post(
            "/api/v1/portfolio/upload",
            data={"name": "Invalid Encoding"},
            files={"file": ("invalid.csv", b"\xff\xfe\x00\x00", "text/csv")},
        )
        assert invalid_encoding.status_code == 400
        assert invalid_encoding.json()["error"]["code"] == "CSV_INVALID_ENCODING"

        oversized = client.post(
            "/api/v1/portfolio/upload",
            data={"name": "Oversized Upload"},
            files={"file": ("large.csv", b"x" * 33, "text/csv")},
        )
        assert oversized.status_code == 413
        assert oversized.json()["error"]["code"] == "CSV_TOO_LARGE"


def test_csv_preview_enforces_structural_resource_limits(tmp_path):
    with build_client(
        tmp_path,
        csv_upload_max_rows=1,
        csv_upload_max_columns=5,
        csv_upload_max_field_characters=64,
        csv_upload_max_cells=100,
    ) as client:
        authenticate(client)

        too_many_rows = client.post(
            "/api/v1/portfolio/upload/preview",
            files={
                "file": (
                    "rows.csv",
                    "ticker,quantity,transaction_date,price\nA.NS,1,2024-01-01,1\nB.NS,1,2024-01-01,1\n",
                    "text/csv",
                )
            },
        )
        assert too_many_rows.status_code == 422
        assert too_many_rows.json()["error"]["code"] == "CSV_TOO_MANY_ROWS"

        too_many_columns = client.post(
            "/api/v1/portfolio/upload/preview",
            files={
                "file": (
                    "columns.csv",
                    "ticker,quantity,transaction_date,price,fees,taxes\nA.NS,1,2024-01-01,1,0,0\n",
                    "text/csv",
                )
            },
        )
        assert too_many_columns.status_code == 422
        assert too_many_columns.json()["error"]["code"] == "CSV_TOO_MANY_COLUMNS"

        long_field = client.post(
            "/api/v1/portfolio/upload/preview",
            files={
                "file": (
                    "field.csv",
                    "ticker,quantity,transaction_date,price,notes\nA.NS,1,2024-01-01,1,"
                    + "x" * 65
                    + "\n",
                    "text/csv",
                )
            },
        )
        assert long_field.status_code == 422
        assert long_field.json()["error"]["code"] == "CSV_FIELD_TOO_LONG"


def test_portfolio_and_manual_trade_limits_are_enforced(tmp_path, monkeypatch):
    monkeypatch.setattr(
        MarketDataService,
        "get_historical_prices",
        lambda self, tickers, start_date, end_date, persist=True: [],
    )
    with build_client(
        tmp_path,
        portfolio_max_per_user=1,
        portfolio_max_trades=1,
    ) as client:
        authenticate(client)
        portfolio = create_portfolio(client)

        extra_portfolio = client.post(
            "/api/v1/portfolio",
            json={"name": "One too many"},
        )
        assert extra_portfolio.status_code == 409
        assert extra_portfolio.json()["error"]["code"] == "PORTFOLIO_LIMIT_REACHED"

        first_trade = client.post(
            f"/api/v1/portfolio/{portfolio['id']}/trades",
            json={
                "ticker": "INFY.NS",
                "quantity": 1,
                "transaction_date": "2024-01-01",
                "price": 100,
            },
        )
        assert first_trade.status_code == 201

        extra_trade = client.post(
            f"/api/v1/portfolio/{portfolio['id']}/trades",
            json={
                "ticker": "TCS.NS",
                "quantity": 1,
                "transaction_date": "2024-01-02",
                "price": 100,
            },
        )
        assert extra_trade.status_code == 409
        assert extra_trade.json()["error"]["code"] == "PORTFOLIO_TRADE_LIMIT_REACHED"
