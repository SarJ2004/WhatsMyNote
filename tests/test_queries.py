import json
from datetime import date

import pytest

from engine import queries
from engine.ledger import apply, open_account, set_budget
from tests.support import ALICE, BOB, role

DAY = date(2026, 9, 26)


def book(conn, user, *actions):
    with conn:
        role(conn, user)
        for action in actions:
            apply(conn, {"currency": "INR", "date": DAY, **action})


def read(conn, user, function, *args, **kwargs):
    with conn:
        role(conn, user)
        return function(conn, *args, **kwargs)


@pytest.fixture
def ledger(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 1000000)
        open_account(conn, "Cash", "INR", 50000)
        set_budget(conn, "food", 50000, "monthly")
        set_budget(conn, "transport", 10000, "weekly")
    book(conn, ALICE,
         {"type": "expense", "amount": 40000, "category": "food", "note": "dinner",
          "raw_text": "spent 400 on dinner"},
         {"type": "expense", "amount": 30000, "category": "food", "note": "groceries",
          "raw_text": "spent 300 on groceries", "date": date(2026, 9, 2)},
         {"type": "expense", "amount": 25000, "category": "transport", "note": "uber",
          "raw_text": "paid 250 for uber", "account": "Cash"},
         {"type": "expense", "amount": 99000, "category": "food", "note": "party",
          "raw_text": "spent 990 on a party", "date": date(2026, 8, 30)},
         {"type": "income", "amount": 5000000, "source": "salary",
          "raw_text": "received 50000 salary"},
         {"type": "lending", "person": "Ravi", "direction": "lent", "amount": 50000,
          "due": date(2026, 9, 20), "raw_text": "lent 500 to Ravi"},
         {"type": "lending", "person": "ravi", "direction": "lent", "repayment": True,
          "amount": 20000, "raw_text": "Ravi paid me back 200"},
         {"type": "lending", "person": "Priya", "direction": "borrowed", "amount": 10000,
          "raw_text": "borrowed 100 from Priya"})
    with conn:
        role(conn, BOB)
        open_account(conn, "HDFC", "INR", 1000000)
    book(conn, BOB, {"type": "expense", "amount": 900000, "category": "food",
                     "raw_text": "bob's feast"},
         {"type": "lending", "person": "Ravi", "direction": "lent", "amount": 70000})
    return conn


def test_spending_excludes_another_users_rows(ledger):
    rows = read(ledger, ALICE, queries.spending_by_category, date(2026, 9, 1), date(2026, 9, 30))
    assert rows == [("food", 70000), ("transport", 25000)]


def test_spending_totals_a_category_over_a_range(ledger):
    rows = read(ledger, ALICE, queries.spending, date(2026, 9, 1), date(2026, 9, 30),
                category="Food")
    assert rows == [{"category": "food", "currency": "INR", "total": 70000, "count": 2}]


def test_spending_can_search_the_words_of_an_entry(ledger):
    rows = read(ledger, ALICE, queries.spending, date(2026, 9, 1), date(2026, 9, 30),
                text="dinner")
    assert rows == [{"category": "food", "currency": "INR", "total": 40000, "count": 1}]


def test_a_search_treats_wildcards_as_plain_text(ledger):
    rows = read(ledger, ALICE, queries.spending, date(2026, 9, 1), date(2026, 9, 30), text="%")
    assert rows == []


def test_income_totals_by_source(ledger):
    rows = read(ledger, ALICE, queries.income, date(2026, 9, 1), date(2026, 9, 30))
    assert rows == [{"source": "salary", "currency": "INR", "total": 5000000, "count": 1}]


def test_owed_nets_repayments_and_flags_what_is_overdue(ledger):
    rows = read(ledger, ALICE, queries.owed, DAY)
    assert rows == [
        {"person": "Priya", "direction": "borrowed", "currency": "INR", "outstanding": 10000,
         "due": None, "overdue": False},
        {"person": "Ravi", "direction": "lent", "currency": "INR", "outstanding": 30000,
         "due": date(2026, 9, 20), "overdue": True},
    ]
    assert read(ledger, ALICE, queries.owed, DAY, direction="lent", person="RAVI") == rows[1:]


def test_budget_status_counts_the_current_period_only(ledger):
    rows = read(ledger, ALICE, queries.budgets, DAY)
    assert rows == [
        {"category": "food", "currency": "INR", "limit": 50000, "spent": 70000,
         "period": "monthly", "start": date(2026, 9, 1), "end": date(2026, 9, 30)},
        {"category": "transport", "currency": "INR", "limit": 10000, "spent": 25000,
         "period": "weekly", "start": date(2026, 9, 21), "end": date(2026, 9, 27)},
    ]


def test_transactions_list_the_largest_first(ledger):
    rows = read(ledger, ALICE, queries.transactions, "expense", date(2026, 8, 1),
                date(2026, 9, 30), order="largest", limit=2)
    assert [(row["label"], row["amount"]) for row in rows] == [("party", 99000), ("dinner", 40000)]


def test_transactions_list_every_kind_most_recent_first(ledger):
    rows = read(ledger, ALICE, queries.transactions, None, date(2026, 9, 1), date(2026, 9, 30),
                limit=20)
    assert {row["kind"] for row in rows} == {"expense", "income", "lending"}
    assert rows[-1]["label"] == "groceries"


def test_candidates_find_an_entry_by_its_words_and_amount(ledger):
    rows = read(ledger, ALICE, queries.candidates, "expense", text="uber")
    assert [(row["label"], row["amount"]) for row in rows] == [("uber", 25000)]
    assert read(ledger, ALICE, queries.candidates, "expense", amount=40000)[0]["label"] == "dinner"
    assert read(ledger, ALICE, queries.candidates, "expense", text="feast") == []
    assert read(ledger, ALICE, queries.candidates, "account", text="cash")[0]["label"] == "Cash"


def test_context_names_the_accounts_and_categories(ledger):
    context = read(ledger, ALICE, queries.context)
    assert context["accounts"] == [
        {"name": "Cash", "currency": "INR", "default": False},
        {"name": "HDFC", "currency": "INR", "default": True},
    ]
    assert set(context["categories"]) == {"food", "transport"}
    assert set(context["people"]) == {"Ravi", "Priya"}


def test_reads_and_writes_filter_by_user_even_without_row_security(ledger):
    """The owner role skips row-level security; the explicit user filter must still hold."""
    from engine.ledger import LedgerError, delete_record, update_record

    with ledger.cursor() as cur:
        cur.execute("select id from records r join expense_records e on e.record_id = r.id "
                    "where r.user_id = %s", (BOB,))
        bobs = cur.fetchone()[0]
    with ledger:
        with ledger.cursor() as cur:
            cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (ALICE,))
        assert {r["name"] for r in queries.balances(ledger)} == {"HDFC", "Cash"}
        assert all(r["person"] != "Ravi" or r["outstanding"] == 30000
                   for r in queries.owed(ledger, DAY))
        assert queries.candidates(ledger, "expense", text="feast") == []
        assert "feast" not in json.dumps(queries.context(ledger))
        assert queries.spending(ledger, date(2026, 9, 1), date(2026, 9, 30), text="feast") == []
        with pytest.raises(LedgerError):
            update_record(ledger, bobs, {"amount": 1})
        with pytest.raises(LedgerError):
            delete_record(ledger, bobs)


def test_the_largest_entries_are_ranked_by_what_they_cost_the_account(conn):
    from decimal import Decimal

    from engine.rates import Converter

    class Rates:
        def get(self, on, base, quote):
            return Decimal("83")

        def last(self, on, base, quote):
            return None

        def put(self, *args):
            pass

    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 1000000)
        apply(conn, {"type": "expense", "amount": 40000, "currency": "INR", "category": "food",
                     "note": "dinner", "date": DAY})
        apply(conn, {"type": "expense", "amount": 1500, "currency": "USD", "category": "software",
                     "note": "domain", "date": DAY}, rates=Converter(Rates(), None))
        rows = queries.transactions(conn, "expense", DAY, DAY, order="largest")
    assert [(r["label"], r["amount"], r["currency"]) for r in rows] == [
        ("domain", 1500, "USD"), ("dinner", 40000, "INR")]
