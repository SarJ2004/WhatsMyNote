import os
from datetime import date, timedelta

import psycopg2
import pytest

from engine.ledger import NeedsConfirmation, apply, confirm, open_account

DSN = os.environ.get(
    "WMN_TEST_DSN", "postgresql://postgres:wmn@localhost:54329/whatsmynote"
)
USER = "11111111-1111-1111-1111-111111111111"


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


def balance_of(conn, user_id, name):
    with conn:
        role(conn, user_id)
        with conn.cursor() as cur:
            cur.execute(
                "select current_balance from account_records a "
                "join records r on r.id = a.record_id where a.name = %s",
                (name,),
            )
            row = cur.fetchone()
            return None if row is None else row[0]


def test_expense_decreases_the_account_balance(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "expense", "account": "HDFC", "amount": 40000,
                     "currency": "INR", "category": "food", "date": date(2026, 9, 26)})
    assert balance_of(conn, USER, "HDFC") == 60000


def test_expense_with_no_account_writes_nothing(conn):
    with conn:
        role(conn, USER)
        with pytest.raises(Exception) as caught:
            apply(conn, {"type": "expense", "amount": 40000, "currency": "INR",
                         "category": "food", "date": date(2026, 9, 26)})
    assert getattr(caught.value, "code", None) == "no_account"


def test_expense_with_no_named_account_uses_the_default(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "Cash", "INR", 50000, is_default=True)
        apply(conn, {"type": "expense", "amount": 10000, "currency": "INR",
                     "category": "food", "date": date(2026, 9, 26)})
    assert balance_of(conn, USER, "Cash") == 40000


def test_transfer_leaves_the_sum_unchanged(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        open_account(conn, "Cash", "INR", 0)
        apply(conn, {"type": "transfer", "source": "HDFC", "destination": "Cash",
                     "amount": 25000, "currency": "INR", "date": date(2026, 9, 26)})
    assert balance_of(conn, USER, "HDFC") + balance_of(conn, USER, "Cash") == 100000


def test_delete_writes_a_confirmation_and_changes_nothing(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        result = apply(conn, {"type": "delete", "record_id": 1})
    assert isinstance(result, NeedsConfirmation)
    assert balance_of(conn, USER, "HDFC") == 100000


def test_replaying_a_confirmation_applies_once(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        result = apply(conn, {"type": "delete", "record_id": 1})
        confirm(conn, result.token)
    with conn:
        role(conn, USER)
        with pytest.raises(Exception):
            confirm(conn, result.token)
    assert balance_of(conn, USER, "HDFC") is None


def test_expired_confirmation_is_rejected(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        result = apply(conn, {"type": "delete", "record_id": 1})
        with conn.cursor() as cur:
            cur.execute(
                "update confirmations set expires_at = now() - interval '1 minute' "
                "where token = %s",
                (result.token,),
            )
    with conn:
        role(conn, USER)
        with pytest.raises(Exception):
            confirm(conn, result.token)
    assert balance_of(conn, USER, "HDFC") == 100000
