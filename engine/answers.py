"""Answers built from typed queries: the facts a sentence may quote, and a plain
sentence that states them with no model at all."""

from datetime import date

from engine import queries
from engine.intent import Action
from engine.money import format_money
from engine.parse import RANGES, date_range
from engine.phrase import Answer, Fact

_PERIODS = {name: words for words, name in RANGES.items()} | {"all": "in all"}
_MOST = 6


def answer(conn, action, today):
    """The answer to one typed question."""
    return {
        "spending": _spending,
        "income": _income,
        "balances": _balances,
        "owed": _owed,
        "budgets": _budgets,
        "transactions": _transactions,
    }[action.metric](conn, action, today)


def combine(answers):
    return Answer([fact for a in answers for fact in a.facts],
                  " ".join(a.plain for a in answers))


def advice(conn, today):
    """What advice may draw on: this month and last month by category, and budgets."""
    this_month = queries.spending(conn, date_range("this_month", today)[0], today)
    last_month = {(r["category"], r["currency"]): r["total"]
                  for r in queries.spending(conn, *date_range("last_month", today))}
    facts = []
    for row in this_month[:_MOST]:
        facts.append(Fact(f"{row['category']} this month",
                          format_money(row["total"], row["currency"])))
        earlier = last_month.get((row["category"], row["currency"]))
        if earlier:
            facts.append(Fact(f"{row['category']} last month",
                              format_money(earlier, row["currency"])))
    for budget in queries.budgets(conn, today):
        facts.append(Fact(f"{budget['category']} {budget['period']} budget",
                          format_money(budget["limit"], budget["currency"])))
    spent = _spending(conn, Action("query", metric="spending", range="this_month"), today)
    return Answer(facts, spent.plain, exhaustive=False)


def _spending(conn, action, today):
    start, end, period = _period(action, today)
    rows = queries.spending(conn, start, end, category=action.category, text=action.note)
    return _totals(rows, "category", "spent", f" on {action.category or action.note}"
                   if action.category or action.note else "", period)


def _income(conn, action, today):
    start, end, period = _period(action, today)
    what = action.category or action.note
    rows = queries.income(conn, start, end, text=what)
    return _totals(rows, "source", "received", f" from {what}" if what else "", period)


def _totals(rows, group, verb, about, period):
    """One total per currency, and a breakdown when the question named no group."""
    if not rows:
        return Answer([], f"You {verb} nothing{about} {period}.")
    totals = {}
    for row in rows:
        totals[row["currency"]] = totals.get(row["currency"], 0) + row["total"]
    amounts = [format_money(total, currency) for currency, total in totals.items()]
    facts = [Fact(f"{verb}{about} {period}", amount) for amount in amounts]
    plain = f"You {verb} {_and(amounts)}{about} {period}"
    if not about and len(rows) > 1:
        parts = [(row[group], format_money(row["total"], row["currency"]))
                 for row in rows[:_MOST]]
        facts += [Fact(name, amount) for name, amount in parts]
        plain += ": " + ", ".join(f"{name} {amount}" for name, amount in parts)
    return Answer(facts, plain + ".")


def _balances(conn, action, today):
    rows = queries.balances(conn)
    if action.account:
        rows = [r for r in rows if r["name"].lower() == action.account.lower()] or rows
    if not rows:
        return Answer([], "You have no accounts yet.")
    facts = [Fact(row["name"], format_money(row["current_balance"], row["currency"]))
             for row in rows]
    return Answer(facts, _and([f"{f.label} has {f.value}" for f in facts]) + ".")


def _owed(conn, action, today):
    rows = queries.owed(conn, today, direction=action.direction, person=action.person)
    if not rows:
        return Answer([], {"lent": "Nobody owes you anything.",
                           "borrowed": "You do not owe anyone anything."}.get(
                               action.direction, "No loans are open."))
    facts, parts = [], []
    for row in rows:
        amount = format_money(row["outstanding"], row["currency"])
        who = (f"{row['person']} owes you" if row["direction"] == "lent"
               else f"you owe {row['person']}")
        when = ""
        if row["due"]:
            when = f"due {_day(row['due'], today)}" + (", overdue" if row["overdue"] else "")
        facts.append(Fact(f"{who}, {when}" if when else who, amount))
        parts.append(f"{who} {amount}" + (f" ({when})" if when else ""))
    return Answer(facts, _capital(_and(parts)) + ".")


def _budgets(conn, action, today):
    rows = queries.budgets(conn, today, category=action.category)
    if not rows:
        return Answer([], f"There is no budget for {action.category}." if action.category
                      else "You have no budgets yet.")
    facts, parts = [], []
    for row in rows:
        spent = format_money(row["spent"], row["currency"])
        limit = format_money(row["limit"], row["currency"])
        span = "this week" if row["period"] == "weekly" else "this month"
        facts += [Fact(f"{row['category']} spent {span}", spent),
                  Fact(f"{row['category']} {row['period']} budget", limit)]
        if row["spent"] > row["limit"]:
            over = format_money(row["spent"] - row["limit"], row["currency"])
            facts.append(Fact(f"{row['category']} over by", over))
            parts.append(f"{row['category']} is over budget: {spent} spent of {limit}, {over} over")
        else:
            left = format_money(row["limit"] - row["spent"], row["currency"])
            facts.append(Fact(f"{row['category']} left", left))
            parts.append(f"{row['category']} is within budget: {spent} spent of {limit}, "
                         f"{left} left")
    return Answer(facts, ". ".join(_capital(p) for p in parts) + ".")


def _transactions(conn, action, today):
    start, end, period = _period(action, today)
    kind = action.entity if action.entity in ("expense", "income", "transfer", "lending") \
        else None
    rows = queries.transactions(conn, kind, start, end, text=action.note,
                                order=action.order or "recent", limit=5)
    noun = f"{kind}s" if kind else "entries"
    if not rows:
        return Answer([], f"No {noun} {period}.")
    entries = [(row["label"], format_money(row["amount"], row["currency"]),
                _day(row["date"], today)) for row in rows]
    which = "largest" if action.order == "largest" else "most recent"
    return Answer([Fact(f"{label} on {day}", amount) for label, amount, day in entries],
                  f"Your {which} {noun} {period}: "
                  + ", ".join(f"{label} {amount} on {day}" for label, amount, day in entries)
                  + ".")


def _period(action, today):
    """The dates a question covers, and how to say them."""
    if action.range == "custom" and (action.start or action.end):
        start, end = sorted((action.start or date(1900, 1, 1), action.end or today))
        return start, end, f"from {_day(start, today)} to {_day(end, today)}"
    name = action.range or "this_month"
    return (*date_range(name, today), _PERIODS.get(name, "this month"))


def _day(day, today):
    return f"{day.day} {day:%b}" if day.year == today.year else f"{day.day} {day:%b %Y}"


def _capital(text):
    return text[:1].upper() + text[1:]


def _and(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
