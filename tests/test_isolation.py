from datetime import date
from pathlib import Path

import psycopg2
import pytest

from engine.ledger import apply, open_account
from tests.support import ALICE, BOB, MIGRATIONS, role


def _alice_books_an_expense(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000, is_default=True)
        apply(conn, {"type": "expense", "account": "HDFC", "amount": 40000,
                     "currency": "INR", "category": "food", "date": date(2026, 9, 26)})


def test_another_users_row_is_invisible_and_untouchable(conn):
    with conn:
        role(conn, ALICE)
        with conn.cursor() as cur:
            cur.execute(
                "insert into records (user_id, record_type, raw_text) "
                "values (%s, 'EXPENSE', 'lunch') returning id",
                (ALICE,),
            )
            row_id = cur.fetchone()[0]

    with conn:
        role(conn, BOB)
        with conn.cursor() as cur:
            cur.execute("select id from records where id = %s", (row_id,))
            assert cur.fetchall() == []
            cur.execute(
                "update records set raw_text = 'stolen' where id = %s", (row_id,)
            )
            assert cur.rowcount == 0


@pytest.mark.parametrize("table", [
    "account_records", "expense_records",
])
def test_another_users_detail_rows_are_invisible_and_untouchable(conn, table):
    _alice_books_an_expense(conn)
    with conn:
        role(conn, BOB)
        with conn.cursor() as cur:
            cur.execute(f"select count(*) from {table}")
            assert cur.fetchone()[0] == 0
            cur.execute(f"update {table} set notes = 'stolen'")
            assert cur.rowcount == 0
            cur.execute(f"delete from {table}")
            assert cur.rowcount == 0


def test_a_detail_row_cannot_be_attached_to_another_users_record(conn):
    _alice_books_an_expense(conn)
    with conn.cursor() as cur:
        cur.execute("select id from records where record_type = 'EXPENSE'")
        alice_record = cur.fetchone()[0]
    with conn:
        role(conn, BOB)
        with conn.cursor() as cur, pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "insert into budget_records (record_id, category, amount, amount_minor, "
                "currency) values (%s, 'food', 1, 1, 'INR')",
                (alice_record,),
            )


def test_another_users_confirmations_are_invisible(conn):
    with conn.cursor() as cur:
        cur.execute(
            "insert into confirmations (token, user_id, action, expires_at) "
            "values ('t', %s, '{}', now() + interval '10 minutes')",
            (ALICE,),
        )
    with conn:
        role(conn, BOB)
        with conn.cursor() as cur:
            cur.execute("select count(*) from confirmations")
            assert cur.fetchone()[0] == 0


def test_anonymous_clients_have_no_access(conn):
    _alice_books_an_expense(conn)
    with conn:
        with conn.cursor() as cur:
            cur.execute("set local role anon")
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute("select count(*) from expense_records")


def test_rates_are_readable_but_not_writable_by_users(conn):
    with conn.cursor() as cur:
        cur.execute("insert into fx_rates values ('2026-09-26', 'USD', 'INR', 83)")
    with conn:
        role(conn, ALICE)
        with conn.cursor() as cur:
            cur.execute("select rate from fx_rates")
            assert cur.fetchone()[0] == 83
            with pytest.raises(psycopg2.errors.InsufficientPrivilege):
                cur.execute("update fx_rates set rate = 1")


def test_usage_counters_are_closed_to_users(conn):
    with conn:
        role(conn, ALICE)
        with conn.cursor() as cur, pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("delete from model_usage")


def test_the_isolation_migration_can_be_applied_again_over_a_live_schema(conn):
    """Staging already has its own tenant_isolation policies. Reapplying must not fail."""
    later = [m for m in MIGRATIONS if not m.name.startswith("0001")]
    assert later, "expected a migration after 0001"
    with conn.cursor() as cur:
        cur.execute(
            "create policy tenant_isolation on expense_records using (true)"
        )
        for migration in later:
            cur.execute(Path(migration).read_text())
            cur.execute(Path(migration).read_text())
        cur.execute(
            "select count(*) from pg_policies where policyname = 'tenant_isolation'"
        )
        assert cur.fetchone()[0] == 0


def test_a_record_inserted_without_timestamps_gets_them(conn):
    """Staging's timestamps had no default, because the old backend filled them in code."""
    later = [m for m in MIGRATIONS if not m.name.startswith("0001")]
    with conn.cursor() as cur:
        cur.execute("alter table records alter column created_at drop default, "
                    "alter column updated_at drop default")
        for migration in later:
            cur.execute(Path(migration).read_text())
    with conn:
        role(conn, ALICE)
        with conn.cursor() as cur:
            cur.execute("insert into records (user_id, record_type, raw_text) "
                        "values (%s, 'EXPENSE', 'lunch') returning created_at, updated_at",
                        (ALICE,))
            created, updated = cur.fetchone()
    assert created is not None and updated is not None


def test_the_legacy_amount_column_holds_whole_units(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "expense", "account": "HDFC", "amount": 40050,
                     "currency": "INR", "category": "food", "date": date(2026, 9, 26)})
        with conn.cursor() as cur:
            cur.execute("select amount, amount_minor from expense_records")
            assert cur.fetchone() == (400, 40050)
