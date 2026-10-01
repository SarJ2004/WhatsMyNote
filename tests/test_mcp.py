"""MCP tools take a bearer token. The engine derives the user from it.

A tool authenticated as one user must not return another user's balance even
when the request names the other user's id. No tool accepts a user id argument.
"""

import asyncio
import inspect
import os

import psycopg2
import pytest

DSN = os.environ.get(
    "WMN_TEST_DSN", "postgresql://postgres:wmn@localhost:54329/whatsmynote"
)
ALICE = "11111111-1111-1111-1111-111111111111"
BOB = "22222222-2222-2222-2222-222222222222"


class Verifier:
    def __init__(self, users):
        self.users = users

    def __call__(self, token):
        return self.users.get(token)


@pytest.fixture
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(open("supabase/migrations/0001_isolation.sql").read())
    conn.close()
    return DSN


def test_tools_take_a_token_and_not_a_user_id():
    from mcp_server.server import TOOLS

    for name in ("log_expense", "log_income", "transfer", "balances", "spending", "ask"):
        signature = inspect.signature(TOOLS[name])
        assert "token" in signature.parameters
        assert "user_id" not in signature.parameters


def test_balances_ignore_a_named_other_user(db):
    from mcp_server.server import build_server

    verifier = Verifier({"alice-token": ALICE, "bob-token": BOB})
    server = build_server(dsn=db, verify=verifier)

    alice = server.call(
        "balances", {"token": "alice-token", "user_id": BOB}
    )
    assert alice == []

    server.call(
        "log_income",
        {
            "token": "bob-token",
            "account": "HDFC",
            "amount": 50000,
            "currency": "INR",
            "source": "salary",
        },
    )
    # Alice names Bob's id. The token, not the argument, decides whose rows return.
    stolen = server.call(
        "balances", {"token": "alice-token", "user_id": BOB}
    )
    assert stolen == []

    bob = server.call("balances", {"token": "bob-token"})
    assert bob == [{"name": "HDFC", "currency": "INR", "current_balance": 50000}]


def test_unauthenticated_tool_returns_the_code(db):
    from mcp_server.server import build_server

    server = build_server(dsn=db, verify=Verifier({}))
    result = server.call("balances", {"token": "nope"})
    assert result["code"] == "unauthenticated"
