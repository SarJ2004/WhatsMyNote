from datetime import date

from engine.ledger import apply, open_account, set_budget
from engine.observe import Observation, observations
from tests.support import ALICE, BOB, role

DAY = date(2026, 9, 26)


def food(amount, day=DAY):
    return {"type": "expense", "amount": amount, "currency": "INR", "category": "food",
            "date": day}


def test_no_observation_on_an_empty_ledger(conn):
    with conn:
        role(conn, ALICE)
        assert observations(conn, DAY) == []


def test_observation_fires_when_spend_exceeds_budget(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        set_budget(conn, "food", 30000, "monthly")
        apply(conn, food(40000))
        found = observations(conn, DAY)
    assert found == [Observation(
        "over_budget", "food", "food is ₹100 over its ₹300 monthly budget")]


def test_no_observation_when_spend_is_within_budget(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        set_budget(conn, "food", 50000, "monthly")
        apply(conn, food(40000))
        found = observations(conn, DAY)
    assert not any(o.kind == "over_budget" for o in found)


def test_a_budget_nearly_used_up_is_mentioned(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        set_budget(conn, "food", 40000, "monthly")
        apply(conn, food(38000))
        found = observations(conn, DAY)
    assert found == [Observation(
        "near_budget", "food", "food has used ₹380 of its ₹400 monthly budget")]


def test_last_months_spending_does_not_count_against_this_month(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 1000000)
        set_budget(conn, "food", 30000, "monthly")
        apply(conn, food(90000, day=date(2026, 8, 30)))
        assert observations(conn, DAY) == []


def test_another_users_spending_never_triggers_an_observation(conn):
    with conn:
        role(conn, BOB)
        open_account(conn, "HDFC", "INR", 1000000)
        apply(conn, food(90000))
    with conn:
        role(conn, ALICE)
        set_budget(conn, "food", 30000, "monthly")
        assert observations(conn, DAY) == []


def test_observation_fires_for_a_debt_past_its_payback_date(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "lending", "person": "Ravi", "direction": "lent", "amount": 50000,
                     "currency": "INR", "date": date(2026, 9, 1), "due": date(2026, 9, 20)})
        apply(conn, {"type": "lending", "person": "Priya", "direction": "borrowed",
                     "amount": 10000, "currency": "INR", "date": date(2026, 9, 1),
                     "due": date(2026, 9, 30)})
        found = observations(conn, DAY)
    assert found == [Observation(
        "overdue_debt", "lending", "Ravi owes you ₹500, due 20 Sep 2026")]


def test_a_repaid_debt_is_not_overdue(conn):
    with conn:
        role(conn, ALICE)
        open_account(conn, "HDFC", "INR", 100000)
        apply(conn, {"type": "lending", "person": "Ravi", "direction": "lent", "amount": 50000,
                     "currency": "INR", "date": date(2026, 9, 1), "due": date(2026, 9, 20)})
        apply(conn, {"type": "lending", "person": "Ravi", "direction": "lent", "amount": 50000,
                     "repayment": True, "currency": "INR", "date": DAY})
        assert observations(conn, DAY) == []
