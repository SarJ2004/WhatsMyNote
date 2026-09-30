"""Deterministic checks over the user's own data, volunteered with an answer.
A model never decides whether one fires; each sentence is built here."""

from dataclasses import dataclass

from engine import queries
from engine.money import format_money

_NEAR = 0.9


@dataclass(frozen=True)
class Observation:
    kind: str
    category: str
    detail: str


def observations(conn, today):
    found = []
    for budget in queries.budgets(conn, today):
        limit, spent = budget["limit"], budget["spent"]
        of_budget = f"{format_money(limit, budget['currency'])} {budget['period']} budget"
        if spent > limit:
            over = format_money(spent - limit, budget["currency"])
            found.append(Observation(
                "over_budget", budget["category"],
                f"{budget['category']} is {over} over its {of_budget}"))
        elif spent >= limit * _NEAR:
            used = format_money(spent, budget["currency"])
            found.append(Observation(
                "near_budget", budget["category"],
                f"{budget['category']} has used {used} of its {of_budget}"))
    for loan in queries.owed(conn, today):
        if loan["overdue"]:
            amount = format_money(loan["outstanding"], loan["currency"])
            due = f"{loan['due'].day} {loan['due']:%b %Y}"
            who = (f"{loan['person']} owes you {amount}" if loan["direction"] == "lent"
                   else f"You owe {loan['person']} {amount}")
            found.append(Observation("overdue_debt", "lending", f"{who}, due {due}"))
    return found
