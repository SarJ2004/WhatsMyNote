"""Deterministic checks over the user's own data. The model only phrases these."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    kind: str
    category: str
    detail: str


def observations(conn, today):
    found = []
    start = today.replace(day=1)
    with conn.cursor() as cur:
        cur.execute(
            "select b.category, b.amount_minor, "
            "coalesce(sum(e.converted_minor), 0) "
            "from budget_records b "
            "left join expense_records e on e.category = b.category "
            "and e.expense_date between %s and %s "
            "group by b.category, b.amount_minor",
            (start, today),
        )
        for category, budget, spent in cur.fetchall():
            if spent > budget:
                found.append(Observation(
                    "over_budget", category,
                    f"{category} is {int(spent) - int(budget)} over its budget",
                ))
    return found
