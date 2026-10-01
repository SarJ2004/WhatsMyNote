import threading
from datetime import date
from decimal import Decimal

import psycopg2
import pytest

from engine.ledger import (
    Booked, LedgerError, NeedsConfirmation, apply, confirm, delete_record,
    open_account, request_confirmation, set_budget, update_record,
)
from engine.rates import Converter
from tests.support import ALICE, BOB, role

USER = ALICE
DAY = date(2026, 9, 26)


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


def expense(amount, **extra):
    return {"type": "expense", "amount": amount, "currency": "INR",
            "category": "food", "date": DAY, **extra}


class RateCache:
    def __init__(self, rates=None):
        self.rates = dict(rates or {})

    def get(self, on, base, quote):
        return self.rates.get((on, base, quote))

    def last(self, on, base, quote):
        return None

    def put(self, on, base, quote, rate):
        self.rates[(on, base, quote)] = rate


def test_expense_decreases_the_account_balance(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, expense(40000, account="HDFC"))
    assert balance_of(conn, USER, "HDFC") == 60000


def test_booking_reports_the_account_it_touched(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "Cash", "INR", 0)
        hdfc = open_account(conn, "HDFC", "INR", 100000)
        result = apply(conn, expense(40000, account="HDFC"))
    assert isinstance(result, Booked)
    assert result.accounts == [hdfc]


def test_account_names_match_without_regard_to_case(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, expense(40000, account="hdfc"))
    assert balance_of(conn, USER, "HDFC") == 60000


def test_a_short_name_finds_the_one_account_it_begins(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC Bank", "INR", 100000)
        open_account(conn, "ICICI Card", "INR", 100000)
        apply(conn, expense(40000, account="hdfc"))
    assert balance_of(conn, USER, "HDFC Bank") == 60000


def test_a_short_name_that_could_mean_two_accounts_is_refused(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC Bank", "INR", 100000)
        open_account(conn, "HDFC Card", "INR", 100000)
        with pytest.raises(LedgerError) as caught:
            apply(conn, expense(40000, account="hdfc"))
    assert caught.value.code == "ambiguous"


def test_booking_reports_the_amount_charged_to_the_account(conn):
    cache = RateCache({(DAY, "USD", "INR"): Decimal("83.2")})
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 1000000)
        booked = apply(conn, {"type": "expense", "amount": 1500, "currency": "USD",
                              "category": "software", "date": DAY},
                       rates=Converter(cache, fetcher=None))
    from engine.money import Money
    assert booked.charged == Money(124800, "INR")


def test_expense_with_no_account_writes_nothing(conn):
    with conn:
        role(conn, USER)
        with pytest.raises(LedgerError) as caught:
            apply(conn, expense(40000))
    assert caught.value.code == "no_account"


def test_another_users_account_is_never_charged(conn):
    with conn:
        role(conn, BOB)
        open_account(conn, "HDFC", "INR", 100000, is_default=True)
    with conn:
        role(conn, ALICE)
        with pytest.raises(LedgerError) as by_default:
            apply(conn, expense(40000))
        with pytest.raises(LedgerError) as by_name:
            apply(conn, expense(40000, account="HDFC"))
    assert by_default.value.code == "no_account"
    assert by_name.value.code == "no_account"
    assert balance_of(conn, BOB, "HDFC") == 100000


def test_expense_with_no_named_account_uses_the_default(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "Cash", "INR", 50000, is_default=True)
        open_account(conn, "HDFC", "INR", 50000)
        apply(conn, expense(10000))
    assert balance_of(conn, USER, "Cash") == 40000


def test_the_first_account_becomes_the_default(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "Cash", "INR", 50000)
        open_account(conn, "HDFC", "INR", 50000)
        apply(conn, expense(10000))
    assert balance_of(conn, USER, "Cash") == 40000
    assert balance_of(conn, USER, "HDFC") == 50000


def test_a_new_default_replaces_the_old_one(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "Cash", "INR", 50000)
        open_account(conn, "HDFC", "INR", 50000, is_default=True)
        apply(conn, expense(10000))
    assert balance_of(conn, USER, "HDFC") == 40000


def test_a_second_account_with_the_same_name_is_refused(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 50000)
        with pytest.raises(LedgerError) as caught:
            open_account(conn, "hdfc", "INR", 0)
    assert caught.value.code == "ambiguous"


def test_an_unsupported_account_currency_is_refused(conn):
    with conn:
        role(conn, USER)
        with pytest.raises(LedgerError) as caught:
            open_account(conn, "Wallet", "BTC", 0)
    assert caught.value.code == "unsupported_currency"


def test_income_increases_the_account_balance(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "income", "amount": 500000, "currency": "INR",
                     "source": "salary", "date": DAY})
    assert balance_of(conn, USER, "HDFC") == 600000


def test_a_non_positive_amount_is_refused(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        with pytest.raises(LedgerError) as caught:
            apply(conn, expense(0))
    assert caught.value.code == "unparseable"


def test_balances_beyond_the_integer_range_are_kept_exactly(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 3_000_000_000)
        apply(conn, {"type": "income", "amount": 2_500_000_000, "currency": "INR",
                     "source": "salary", "date": DAY})
    assert balance_of(conn, USER, "HDFC") == 5_500_000_000


def test_transfer_leaves_the_sum_unchanged(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        open_account(conn, "Cash", "INR", 0)
        result = apply(conn, {"type": "transfer", "source": "HDFC", "destination": "Cash",
                              "amount": 25000, "currency": "INR", "date": DAY})
    assert balance_of(conn, USER, "HDFC") + balance_of(conn, USER, "Cash") == 100000
    assert balance_of(conn, USER, "Cash") == 25000
    assert len(result.accounts) == 2


def test_a_transfer_to_the_same_account_is_refused(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        with pytest.raises(LedgerError) as caught:
            apply(conn, {"type": "transfer", "source": "HDFC", "destination": "hdfc",
                         "amount": 25000, "currency": "INR", "date": DAY})
    assert caught.value.code == "ambiguous"


def test_lending_moves_money_out_and_a_repayment_brings_it_back(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "lending", "person": "John", "direction": "lent",
                     "amount": 5000, "currency": "INR", "date": DAY})
    assert balance_of(conn, USER, "HDFC") == 95000
    with conn:
        role(conn, USER)
        apply(conn, {"type": "lending", "person": "john", "direction": "lent",
                     "repayment": True, "amount": 5000, "currency": "INR", "date": DAY})
        with conn.cursor() as cur:
            cur.execute("select count(*) from records where record_type = 'LENDING' "
                        "and settled_at is null")
            open_rows = cur.fetchone()[0]
    assert balance_of(conn, USER, "HDFC") == 100000
    assert open_rows == 0


def test_borrowing_brings_money_in(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "lending", "person": "Priya", "direction": "borrowed",
                     "amount": 20000, "currency": "INR", "date": DAY})
    assert balance_of(conn, USER, "HDFC") == 120000


def test_a_repayment_larger_than_the_debt_is_refused(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "lending", "person": "John", "direction": "lent",
                     "amount": 5000, "currency": "INR", "date": DAY})
        with pytest.raises(LedgerError) as caught:
            apply(conn, {"type": "lending", "person": "John", "direction": "lent",
                         "repayment": True, "amount": 9000, "currency": "INR", "date": DAY})
    assert caught.value.code == "ambiguous"


def test_a_foreign_expense_is_converted_into_the_account_currency(conn):
    cache = RateCache({(DAY, "USD", "INR"): Decimal("83.2")})
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 1000000)
        apply(conn, {"type": "expense", "amount": 1500, "currency": "USD",
                     "category": "software", "date": DAY},
              rates=Converter(cache, fetcher=None))
        with conn.cursor() as cur:
            cur.execute("select amount_minor, currency, converted_minor, "
                        "converted_currency, fx_rate from expense_records")
            stored = cur.fetchone()
    assert balance_of(conn, USER, "HDFC") == 1000000 - 124800
    assert stored == (1500, "USD", 124800, "INR", Decimal("83.2"))


def test_a_foreign_expense_with_no_rate_books_nothing(conn):
    def down(base, quote, on):
        raise RuntimeError("down")

    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 1000000)
    with conn:
        role(conn, USER)
        with pytest.raises(LedgerError) as caught:
            apply(conn, {"type": "expense", "amount": 1500, "currency": "USD",
                         "category": "software", "date": DAY},
                  rates=Converter(RateCache(), fetcher=down))
    assert caught.value.code == "rate_unavailable"
    assert balance_of(conn, USER, "HDFC") == 1000000


def test_delete_writes_a_confirmation_and_changes_nothing(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        result = request_confirmation(conn, {"type": "delete", "record_id": 1}, "Delete?")
    assert isinstance(result, NeedsConfirmation)
    assert balance_of(conn, USER, "HDFC") == 100000


def test_confirming_a_delete_gives_the_money_back(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        booked = apply(conn, expense(40000))
        pending = request_confirmation(
            conn, {"type": "delete", "record_id": booked.record_id}, "Delete dinner?")
    assert balance_of(conn, USER, "HDFC") == 60000
    with conn:
        role(conn, USER)
        confirm(conn, pending.token)
    assert balance_of(conn, USER, "HDFC") == 100000


def test_deleting_a_transfer_restores_both_accounts(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        open_account(conn, "Cash", "INR", 0)
        booked = apply(conn, {"type": "transfer", "source": "HDFC", "destination": "Cash",
                              "amount": 25000, "currency": "INR", "date": DAY})
        delete_record(conn, booked.record_id)
    assert balance_of(conn, USER, "HDFC") == 100000
    assert balance_of(conn, USER, "Cash") == 0


def test_updating_an_amount_moves_the_balance_by_the_difference(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        booked = apply(conn, expense(40000))
        update_record(conn, booked.record_id, {"amount": 45000})
    assert balance_of(conn, USER, "HDFC") == 55000


def test_moving_an_expense_to_another_account_moves_the_money(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        open_account(conn, "Cash", "INR", 100000)
        booked = apply(conn, expense(40000, account="HDFC"))
        result = update_record(conn, booked.record_id, {"account": "cash", "category": "Travel"})
        with conn.cursor() as cur:
            cur.execute("select category, payment_source from expense_records")
            stored = cur.fetchone()
    assert balance_of(conn, USER, "HDFC") == 100000
    assert balance_of(conn, USER, "Cash") == 60000
    assert stored == ("travel", "Cash")
    assert len(result.accounts) == 2


def test_renaming_an_account_keeps_its_history_attached(conn):
    with conn:
        role(conn, USER)
        account = open_account(conn, "HDFC", "INR", 100000)
        booked = apply(conn, expense(40000))
        update_record(conn, account, {"name": "HDFC Bank"})
        delete_record(conn, booked.record_id)
    assert balance_of(conn, USER, "HDFC Bank") == 100000


def test_another_users_record_cannot_be_changed_or_deleted(conn):
    with conn:
        role(conn, BOB)
        open_account(conn, "HDFC", "INR", 100000)
        booked = apply(conn, expense(40000))
    with conn:
        role(conn, ALICE)
        with pytest.raises(LedgerError):
            update_record(conn, booked.record_id, {"amount": 1})
    with conn:
        role(conn, ALICE)
        with pytest.raises(LedgerError):
            delete_record(conn, booked.record_id)
    assert balance_of(conn, BOB, "HDFC") == 60000


def test_another_users_confirmation_cannot_be_used(conn):
    with conn:
        role(conn, BOB)
        open_account(conn, "HDFC", "INR", 100000)
        booked = apply(conn, expense(40000))
        pending = request_confirmation(
            conn, {"type": "delete", "record_id": booked.record_id}, "Delete?")
    with conn:
        role(conn, ALICE)
        with pytest.raises(LedgerError):
            confirm(conn, pending.token)
    assert balance_of(conn, BOB, "HDFC") == 60000


def test_replaying_a_confirmation_applies_once(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        result = request_confirmation(conn, {"type": "delete", "record_id": 1}, "Delete?")
        confirm(conn, result.token)
    with conn:
        role(conn, USER)
        with pytest.raises(LedgerError):
            confirm(conn, result.token)
    assert balance_of(conn, USER, "HDFC") is None


def test_expired_confirmation_is_rejected(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        result = request_confirmation(conn, {"type": "delete", "record_id": 1}, "Delete?")
        with conn.cursor() as cur:
            cur.execute(
                "update confirmations set expires_at = now() - interval '1 minute' "
                "where token = %s",
                (result.token,),
            )
    with conn:
        role(conn, USER)
        with pytest.raises(LedgerError):
            confirm(conn, result.token)
    assert balance_of(conn, USER, "HDFC") == 100000


def test_a_second_budget_for_a_category_replaces_the_first(conn):
    with conn:
        role(conn, USER)
        set_budget(conn, "food", 30000, "monthly")
        set_budget(conn, "Food", 50000, "weekly")
        with conn.cursor() as cur:
            cur.execute("select category, amount_minor, period from budget_records")
            rows = cur.fetchall()
    assert rows == [("food", 50000, "weekly")]


def test_two_concurrent_expenses_on_one_account_both_land(dsn, conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)

    barrier = threading.Barrier(2)
    errors = []

    def book():
        c = psycopg2.connect(dsn)
        try:
            with c:
                role(c, USER)
                barrier.wait()
                apply(c, expense(10000))
        except Exception as error:  # pragma: no cover - the assertion reports it
            errors.append(error)
        finally:
            c.close()

    threads = [threading.Thread(target=book) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert balance_of(conn, USER, "HDFC") == 80000


def _blocked(dsn, pid):
    """Whether the backend with this pid is waiting on a lock."""
    probe = psycopg2.connect(dsn)
    try:
        with probe.cursor() as cur:
            cur.execute("select wait_event_type from pg_stat_activity where pid = %s", (pid,))
            row = cur.fetchone()
        return row is not None and row[0] == "Lock"
    finally:
        probe.close()


def _wait_until_blocked(dsn, pid):
    import time

    for _ in range(200):
        if _blocked(dsn, pid):
            return
        time.sleep(0.01)
    raise AssertionError("the second transaction never waited for the first")


def test_a_delete_waiting_on_a_rename_still_gives_the_money_back(dsn, conn):
    with conn:
        role(conn, USER)
        account = open_account(conn, "HDFC", "INR", 1000000)
        booked = apply(conn, expense(50000))
    renamer = psycopg2.connect(dsn)
    deleter = psycopg2.connect(dsn)
    try:
        role(renamer, USER)
        update_record(renamer, account, {"name": "HDFC Bank"})
        errors = []

        def delete():
            try:
                with deleter:
                    role(deleter, USER)
                    delete_record(deleter, booked.record_id)
            except Exception as error:  # pragma: no cover - the assertion reports it
                errors.append(error)

        thread = threading.Thread(target=delete)
        thread.start()
        _wait_until_blocked(dsn, deleter.get_backend_pid())
        renamer.commit()
        thread.join()
    finally:
        renamer.close()
        deleter.close()
    assert errors == []
    assert balance_of(conn, USER, "HDFC Bank") == 1000000


def test_two_accounts_opened_at_once_cannot_share_a_name(dsn):
    barrier = threading.Barrier(2)
    outcomes = []

    def open_one():
        c = psycopg2.connect(dsn)
        try:
            with c:
                role(c, USER)
                barrier.wait()
                open_account(c, "HDFC", "INR", 0)
            outcomes.append("opened")
        except LedgerError as error:
            outcomes.append(error.code)
        finally:
            c.close()

    threads = [threading.Thread(target=open_one) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["ambiguous", "opened"]


def test_renaming_the_person_on_a_loan_moves_all_of_their_entries(conn):
    from engine.queries import owed

    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        loan = apply(conn, {"type": "lending", "person": "Ravi", "direction": "lent",
                            "amount": 80000, "currency": "INR", "date": DAY})
        apply(conn, {"type": "lending", "person": "Ravi", "direction": "lent",
                     "repayment": True, "amount": 50000, "currency": "INR", "date": DAY})
        update_record(conn, loan.record_id, {"person": "Ravinder"})
        rows = owed(conn, DAY)
    assert [(r["person"], r["outstanding"]) for r in rows] == [("Ravinder", 30000)]


def _sum_of_entries(conn, user, name):
    with conn:
        role(conn, user)
        with conn.cursor() as cur:
            cur.execute("select opening_balance from account_records where name = %s", (name,))
            opening = cur.fetchone()[0]
            cur.execute("select coalesce(sum(converted_minor), 0) from expense_records "
                        "where payment_source = %s", (name,))
            spent = cur.fetchone()[0]
            cur.execute("select coalesce(sum(converted_minor), 0) from income_records "
                        "where deposit_account = %s", (name,))
            earned = cur.fetchone()[0]
            cur.execute("select coalesce(sum(case when source_account = %s then -amount_minor "
                        "else converted_minor end), 0) from transfer_records "
                        "where %s in (source_account, destination_account)", (name, name))
            moved = cur.fetchone()[0]
            cur.execute("select coalesce(sum(case when (direction = 'LENT') = is_repayment "
                        "then converted_minor else -converted_minor end), 0) "
                        "from lending_records where account = %s", (name,))
            lent = cur.fetchone()[0]
    return opening - spent + earned + moved + lent


ENTRIES = {
    "expense": ({"type": "expense", "amount": 40000, "category": "food"},
                {"amount": 45000, "account": "Cash", "category": "travel"}),
    "income": ({"type": "income", "amount": 500000, "source": "salary"},
               {"amount": 600000, "account": "Cash", "source": "bonus"}),
    "transfer": ({"type": "transfer", "amount": 25000, "source": "HDFC", "destination": "Cash"},
                 {"amount": 30000, "account": "Cash", "to_account": "HDFC"}),
    "lending": ({"type": "lending", "amount": 20000, "person": "Ravi", "direction": "lent"},
                {"amount": 15000, "account": "Cash", "person": "Asha"}),
    "borrowing": ({"type": "lending", "amount": 20000, "person": "Priya", "direction": "borrowed"},
                  {"amount": 35000, "account": "Cash"}),
}


@pytest.mark.parametrize("kind", ENTRIES)
def test_every_kind_of_entry_keeps_balances_equal_to_its_entries(conn, kind):
    entry, changes = ENTRIES[kind]
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 1000000)
        open_account(conn, "Cash", "INR", 100000)
        booked = apply(conn, {"currency": "INR", "date": DAY, **entry})
        update_record(conn, booked.record_id, changes)
    for name in ("HDFC", "Cash"):
        assert balance_of(conn, USER, name) == _sum_of_entries(conn, USER, name)
    with conn:
        role(conn, USER)
        delete_record(conn, booked.record_id)
    assert balance_of(conn, USER, "HDFC") == 1000000
    assert balance_of(conn, USER, "Cash") == 100000


def test_a_budget_and_an_account_can_be_changed(conn):
    with conn:
        role(conn, USER)
        account = open_account(conn, "HDFC", "INR", 100000)
        budget = set_budget(conn, "food", 30000)
        update_record(conn, budget, {"amount": 40000, "period": "weekly", "category": "meals"})
        update_record(conn, account, {"amount": 12345})
        with conn.cursor() as cur:
            cur.execute("select category, amount_minor, period from budget_records")
            assert cur.fetchone() == ("meals", 40000, "weekly")
    assert balance_of(conn, USER, "HDFC") == 12345


def test_a_used_confirmation_is_refused_as_gone(conn):
    with conn:
        role(conn, USER)
        open_account(conn, "HDFC", "INR", 100000)
        booked = apply(conn, expense(1000))
        pending = request_confirmation(conn, {"type": "delete", "record_id": booked.record_id},
                                       "Delete?")
        confirm(conn, pending.token)
    with conn:
        role(conn, USER)
        with pytest.raises(LedgerError) as caught:
            confirm(conn, pending.token)
    assert caught.value.status == 410


def test_a_transfer_between_currencies_credits_the_converted_amount(conn):
    cache = RateCache({(DAY, "USD", "INR"): Decimal("83")})
    with conn:
        role(conn, USER)
        open_account(conn, "Wise", "USD", 100000)
        open_account(conn, "HDFC", "INR", 0)
        booked = apply(conn, {"type": "transfer", "source": "Wise", "destination": "HDFC",
                              "amount": 10000, "date": DAY},
                       rates=Converter(cache, fetcher=None))
    assert balance_of(conn, USER, "Wise") == 90000
    assert balance_of(conn, USER, "HDFC") == 830000
    with conn:
        role(conn, USER)
        delete_record(conn, booked.record_id)
    assert (balance_of(conn, USER, "Wise"), balance_of(conn, USER, "HDFC")) == (100000, 0)
