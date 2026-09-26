import os
from datetime import date

import psycopg2
import pytest

from engine.ledger import apply, open_account
from engine.queries import spending_by_category

DSN = os.environ.get(
    "WMN_TEST_DSN", "postgresql://postgres:wmn@localhost:54329/whatsmynote"
)
ALICE = "11111111-1111-1111-1111-111111111111"
BOB = "22222222-2222-2222-2222-222222222222"


def role(conn, user_id):
    with conn.cursor() as cur:
        cur.execute("set local role authenticated")
        cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (user_id,))


@pytest.fixture
def conn():
    c = psycopg2.connect(DSN)
    c.autocommit = True
    with c.cursor() as cur:
        cur.execute(open("supabase/migrations/0001_isolation.sql").read())
    yield c
    c.close()


def test_spending_excludes_another_users_rows(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "expense", "account": "HDFC", "amount": 40000,
                     "currency": "INR", "category": "food", "date": date(2026, 9, 26)})
    with conn:
        role(conn, BOB)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "expense", "account": "HDFC", "amount": 900000,
                     "currency": "INR", "category": "food", "date": date(2026, 9, 26)})
    with conn:
        role(conn, ALICE)
        rows = spending_by_category(conn, date(2026, 9, 1), date(2026, 9, 30))
    assert rows == [("food", 40000)]
