import os

import psycopg2
import pytest
from fastapi.testclient import TestClient

DSN = os.environ.get(
    "WMN_TEST_DSN", "postgresql://postgres:wmn@localhost:54329/whatsmynote"
)


class Verifier:
    """Stands in for Supabase. Maps a token to a user id, or rejects it."""

    def __init__(self, users):
        self.users = users
        self.calls = 0

    def __call__(self, token):
        self.calls += 1
        return self.users.get(token)


@pytest.fixture
def client():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(open("supabase/migrations/0001_isolation.sql").read())
    conn.close()

    from engine.api import build_app

    verifier = Verifier({"alice-token": "11111111-1111-1111-1111-111111111111"})
    app = build_app(dsn=DSN, verify=verifier)
    return TestClient(app), verifier


def test_health_is_public(client):
    api, _ = client
    response = api.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_request_without_a_token_is_unauthenticated(client):
    api, _ = client
    response = api.post("/chat", json={"message": "spent 400 on dinner"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_chat_books_an_expense_against_an_account(client):
    api, _ = client
    api.post("/accounts", json={"name": "HDFC", "currency": "INR", "opening_balance": 100000},
             headers={"authorization": "Bearer alice-token"})
    response = api.post("/chat", json={"message": "spent 400 on dinner"},
                        headers={"authorization": "Bearer alice-token"})
    assert response.status_code == 200
    assert response.json()["balance"] == 60000


def test_chat_with_no_account_books_nothing(client):
    api, _ = client
    response = api.post("/chat", json={"message": "spent 400 on dinner"},
                        headers={"authorization": "Bearer alice-token"})
    assert response.status_code == 422
    assert response.json()["code"] == "no_account"


def test_verified_token_is_reused_within_the_window(client):
    api, verifier = client
    for _ in range(3):
        api.get("/balances", headers={"authorization": "Bearer alice-token"})
    assert verifier.calls == 1
