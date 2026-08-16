from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.api.main import create_app
from src.config.settings import Settings


def build_client(tmp_path) -> TestClient:
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{tmp_path / 'authorization.db'}",
        run_migrations_on_startup=True,
        auth_secret_key="authorization-test-secret",
    )
    return TestClient(create_app(settings))


def signup_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "strong-password",
            "full_name": email.split("@")[0],
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_portfolio(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post(
        "/api/v1/portfolio",
        headers=headers,
        json={
            "name": name,
            "base_currency": "INR",
            "benchmark": "NIFTY50",
        },
    )
    assert response.status_code == 201
    return response.json()


def add_trade(client: TestClient, headers: dict[str, str], portfolio_id: int) -> dict:
    response = client.post(
        f"/api/v1/portfolio/{portfolio_id}/trades",
        headers=headers,
        json={
            "ticker": "RELIANCE.NS",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 2500,
            "transaction_date": "2024-01-01",
        },
    )
    assert response.status_code == 201
    return response.json()


def assert_portfolio_hidden(response) -> None:
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PORTFOLIO_NOT_FOUND"


def test_users_only_list_their_own_portfolios(tmp_path):
    with build_client(tmp_path) as client:
        user_a = signup_headers(client, "user-a@example.com")
        user_b = signup_headers(client, "user-b@example.com")

        portfolio_a = create_portfolio(client, user_a, "User A Portfolio")
        portfolio_b = create_portfolio(client, user_b, "User B Portfolio")

        list_a = client.get("/api/v1/portfolio", headers=user_a)
        list_b = client.get("/api/v1/portfolio", headers=user_b)

        assert [item["id"] for item in list_a.json()] == [portfolio_a["id"]]
        assert [item["id"] for item in list_b.json()] == [portfolio_b["id"]]


def test_user_cannot_read_update_or_delete_another_users_portfolio(tmp_path):
    with build_client(tmp_path) as client:
        owner = signup_headers(client, "owner@example.com")
        intruder = signup_headers(client, "intruder@example.com")
        portfolio = create_portfolio(client, owner, "Private Portfolio")

        assert_portfolio_hidden(
            client.get(f"/api/v1/portfolio/{portfolio['id']}", headers=intruder)
        )
        assert_portfolio_hidden(
            client.put(
                f"/api/v1/portfolio/{portfolio['id']}",
                headers=intruder,
                json={"name": "Changed by intruder"},
            )
        )
        assert_portfolio_hidden(
            client.delete(f"/api/v1/portfolio/{portfolio['id']}", headers=intruder)
        )

        owner_read = client.get(f"/api/v1/portfolio/{portfolio['id']}", headers=owner)
        assert owner_read.status_code == 200
        assert owner_read.json()["name"] == "Private Portfolio"


def test_user_cannot_access_or_mutate_another_users_trades_positions_or_summary(tmp_path):
    with build_client(tmp_path) as client:
        owner = signup_headers(client, "trade-owner@example.com")
        intruder = signup_headers(client, "trade-intruder@example.com")
        portfolio = create_portfolio(client, owner, "Trade Owner Portfolio")
        trade = add_trade(client, owner, portfolio["id"])

        protected_paths = [
            f"/api/v1/portfolio/{portfolio['id']}/trades",
            f"/api/v1/portfolio/{portfolio['id']}/positions",
            f"/api/v1/portfolio/{portfolio['id']}/returns",
            f"/api/v1/portfolio/{portfolio['id']}/summary",
        ]
        for path in protected_paths:
            assert_portfolio_hidden(client.get(path, headers=intruder))

        assert_portfolio_hidden(
            client.post(
                f"/api/v1/portfolio/{portfolio['id']}/trades",
                headers=intruder,
                json={
                    "ticker": "INFY.NS",
                    "transaction_type": "BUY",
                    "quantity": 1,
                    "price": 100,
                    "transaction_date": "2024-01-02",
                },
            )
        )
        assert_portfolio_hidden(
            client.put(
                f"/api/v1/portfolio/{portfolio['id']}/trades/{trade['id']}",
                headers=intruder,
                json={"quantity": 99},
            )
        )
        assert_portfolio_hidden(
            client.delete(
                f"/api/v1/portfolio/{portfolio['id']}/trades/{trade['id']}",
                headers=intruder,
            )
        )

        owner_trades = client.get(
            f"/api/v1/portfolio/{portfolio['id']}/trades",
            headers=owner,
        )
        assert owner_trades.status_code == 200
        assert len(owner_trades.json()) == 1


def test_user_cannot_run_analytics_on_another_users_portfolio(tmp_path):
    with build_client(tmp_path) as client:
        owner = signup_headers(client, "analytics-owner@example.com")
        intruder = signup_headers(client, "analytics-intruder@example.com")
        portfolio = create_portfolio(client, owner, "Analytics Owner Portfolio")
        add_trade(client, owner, portfolio["id"])

        risk = client.get(
            f"/api/v1/analytics/portfolio/{portfolio['id']}/risk",
            headers=intruder,
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert_portfolio_hidden(risk)

        regime = client.post(
            f"/api/v1/analytics/portfolio/{portfolio['id']}/regime",
            headers=intruder,
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            },
        )
        assert_portfolio_hidden(regime)
