"""Typed reads. The model never sees these and never writes SQL.

Every read joins the owning record and filters by the user the transaction role
names, on top of row-level security, so a missing role and a missing filter
each fail on their own. Amounts are summed in the currency they were booked
into, so two currencies are never added together.
"""

from engine.parse import date_range

# The caller, as text: user ids are uuid in a new database and varchar in an older one.
_ME = "nullif(current_setting('request.jwt.claim.sub', true), '')"

# One row per entry, in one shape, for lists and for finding what to change. An
# entry's amount is the one the person typed, in the currency they typed it in;
# its cost is what it moved in the account's currency, which is what ranks it.
_ENTRIES = {
    "expense": (
        "e.expense_date, e.amount_minor, e.currency, "
        "coalesce(e.item, e.merchant, e.category), "
        "concat_ws(' ', e.category, e.item, e.merchant, e.payment_source, r.raw_text), "
        "e.converted_minor from expense_records e join records r on r.id = e.record_id"
    ),
    "income": (
        "i.income_date, i.amount_minor, i.currency, "
        "i.source, concat_ws(' ', i.source, i.deposit_account, r.raw_text), "
        "i.converted_minor from income_records i join records r on r.id = i.record_id"
    ),
    "transfer": (
        "t.transfer_date, t.amount_minor, t.currency, "
        "t.source_account || ' to ' || t.destination_account, "
        "concat_ws(' ', t.source_account, t.destination_account, r.raw_text), "
        "t.amount_minor from transfer_records t join records r on r.id = t.record_id"
    ),
    "lending": (
        "coalesce(l.lending_date, r.created_at::date), l.amount_minor, l.currency, l.person, "
        "concat_ws(' ', l.person, l.account, r.raw_text), "
        "l.converted_minor from lending_records l join records r on r.id = l.record_id"
    ),
    "account": (
        "r.created_at::date, a.current_balance, a.currency, a.name, a.name, "
        "a.current_balance from account_records a join records r on r.id = a.record_id"
    ),
    "budget": (
        "r.created_at::date, b.amount_minor, b.currency, b.category, b.category, "
        "b.amount_minor from budget_records b join records r on r.id = b.record_id"
    ),
}


def balances(conn):
    with conn.cursor() as cur:
        cur.execute(
            "select a.name, a.currency, a.current_balance from account_records a "
            f"join records r on r.id = a.record_id where r.user_id::text = {_ME} "
            "order by a.name"
        )
        return [
            {"name": row[0], "currency": row[1].strip(), "current_balance": int(row[2])}
            for row in cur.fetchall()
        ]


def account_balances(conn, account_ids):
    """Name, currency, and balance of the given accounts, in the order given."""
    if not account_ids:
        return []
    with conn.cursor() as cur:
        cur.execute(
            "select a.record_id, a.name, a.currency, a.current_balance from account_records a "
            f"join records r on r.id = a.record_id where r.user_id::text = {_ME} "
            "and a.record_id = any(%s)",
            (list(account_ids),),
        )
        found = {row[0]: {"name": row[1], "currency": row[2].strip(), "balance": int(row[3])}
                 for row in cur.fetchall()}
    return [found[i] for i in account_ids if i in found]


def spending_by_category(conn, start, end):
    with conn.cursor() as cur:
        cur.execute(
            "select category, sum(converted_minor) from expense_records e "
            f"join records r on r.id = e.record_id where r.user_id::text = {_ME} "
            "and e.expense_date between %s and %s "
            "group by category order by category",
            (start, end),
        )
        return [(row[0], int(row[1])) for row in cur.fetchall()]


def spending(conn, start, end, category=None, text=None):
    clauses, params = _filters(category, "lower(e.category) = %s", text,
                               "concat_ws(' ', e.category, e.item, e.merchant, r.raw_text)")
    with conn.cursor() as cur:
        cur.execute(
            "select e.category, coalesce(e.converted_currency, e.currency), "
            "sum(e.converted_minor), count(*) from expense_records e "
            f"join records r on r.id = e.record_id where r.user_id::text = {_ME} "
            "and e.expense_date between %s and %s" + clauses +
            " group by 1, 2 order by 3 desc, 1",
            [start, end] + params,
        )
        return [{"category": row[0], "currency": row[1].strip(), "total": int(row[2]),
                 "count": row[3]} for row in cur.fetchall()]


def income(conn, start, end, text=None):
    clauses, params = _filters(None, None, text, "concat_ws(' ', i.source, r.raw_text)")
    with conn.cursor() as cur:
        cur.execute(
            "select i.source, coalesce(i.converted_currency, i.currency), "
            "sum(i.converted_minor), count(*) from income_records i "
            f"join records r on r.id = i.record_id where r.user_id::text = {_ME} "
            "and i.income_date between %s and %s" + clauses +
            " group by 1, 2 order by 3 desc, 1",
            [start, end] + params,
        )
        return [{"source": row[0], "currency": row[1].strip(), "total": int(row[2]),
                 "count": row[3]} for row in cur.fetchall()]


def owed(conn, today, direction=None, person=None):
    """Open loans: what each person owes you (lent) or you owe them (borrowed)."""
    clauses, params = "", []
    if direction:
        clauses += " and l.direction = %s"
        params.append(direction.upper())
    if person:
        clauses += " and lower(l.person) = lower(%s)"
        params.append(person)
    with conn.cursor() as cur:
        cur.execute(
            "select (array_agg(l.person order by r.id))[1], lower(l.direction::text), l.currency, "
            "sum(case when l.is_repayment then -l.amount_minor else l.amount_minor end), "
            "min(l.expected_payback_by) filter (where not l.is_repayment) "
            "from lending_records l join records r on r.id = l.record_id "
            f"where r.user_id::text = {_ME}" + clauses +
            " group by lower(l.person), l.direction, l.currency "
            "having sum(case when l.is_repayment then -l.amount_minor "
            "else l.amount_minor end) > 0 order by 1, 2",
            params,
        )
        return [{"person": row[0], "direction": row[1], "currency": row[2].strip(),
                 "outstanding": int(row[3]), "due": row[4],
                 "overdue": row[4] is not None and row[4] < today}
                for row in cur.fetchall()]


def budgets(conn, today, category=None):
    """Each budget against what has been spent in its current period, in one query."""
    week, month = date_range("this_week", today), date_range("this_month", today)
    with conn.cursor() as cur:
        cur.execute(
            "select b.category, b.currency, b.amount_minor, b.period, p.start, p.finish, "
            "coalesce((select sum(e.converted_minor) from expense_records e "
            "join records er on er.id = e.record_id "
            f"where er.user_id::text = {_ME} and lower(e.category) = lower(b.category) "
            "and e.expense_date between p.start and p.finish "
            "and coalesce(e.converted_currency, e.currency) = b.currency), 0) "
            "from budget_records b join records r on r.id = b.record_id "
            "cross join lateral (select case when b.period = 'weekly' then %s::date "
            "else %s::date end as start, case when b.period = 'weekly' then %s::date "
            "else %s::date end as finish) p "
            f"where r.user_id::text = {_ME}"
            + (" and lower(b.category) = lower(%s)" if category else "")
            + " order by b.category",
            [week[0], month[0], week[1], month[1]] + ([category] if category else []),
        )
        return [{"category": row[0], "currency": row[1].strip(), "limit": int(row[2]),
                 "spent": int(row[6]), "period": row[3], "start": row[4], "end": row[5]}
                for row in cur.fetchall()]


def records(conn, record_type="", start="", end="", text=""):
    """Entries as the site lists them, most recent first."""
    clauses, params = [f"r.user_id::text = {_ME}"], []
    if record_type:
        clauses.append("r.record_type::text = %s")
        params.append(record_type.upper())
    if start:
        clauses.append("r.created_at::date >= %s")
        params.append(start)
    if end:
        clauses.append("r.created_at::date <= %s")
        params.append(end)
    if text:
        clauses.append("r.raw_text ilike %s escape '\\'")
        params.append(_like(text))
    with conn.cursor() as cur:
        cur.execute(
            "select r.created_at::date, r.record_type, r.raw_text from records r where "
            + " and ".join(clauses) + " order by r.created_at desc, r.id desc",
            params,
        )
        return [{"date": str(row[0]), "record_type": row[1], "raw_text": row[2]}
                for row in cur.fetchall()]


def budget(conn, record_id):
    with conn.cursor() as cur:
        cur.execute(
            "select b.category, b.amount_minor, b.currency, b.period from budget_records b "
            f"join records r on r.id = b.record_id where r.user_id::text = {_ME} "
            "and b.record_id = %s",
            (record_id,),
        )
        row = cur.fetchone()
    return {"category": row[0], "amount": int(row[1]), "currency": row[2].strip(),
            "period": row[3]}


def transactions(conn, kind, start, end, text=None, order="recent", limit=5):
    kinds = [kind] if kind else ["expense", "income", "transfer", "lending"]
    return _entries(conn, kinds, text=text, start=start, end=end,
                    order="cost desc, day desc, id desc" if order == "largest"
                    else "day desc, id desc",
                    limit=limit)


def candidates(conn, kind, text=None, amount=None, day=None, limit=10):
    """Entries a change or delete might mean, most recent first."""
    return _entries(conn, [kind], text=text, amount=amount, start=day, end=day,
                    order="day desc, id desc", limit=limit)


def context(conn):
    """What the model may see to judge a message: names, never amounts or ids.
    One round trip, since it sits on the path of every model turn."""
    with conn.cursor() as cur:
        cur.execute(
            "select "
            "(select coalesce(json_agg(json_build_object('name', a.name, 'currency', "
            "trim(a.currency), 'default', a.is_default) order by a.name), '[]') "
            "from account_records a join records r on r.id = a.record_id "
            f"where r.user_id::text = {_ME}), "
            "(select coalesce(json_agg(category order by seen desc), '[]') from ("
            "select category, max(seen) as seen from ("
            "select lower(b.category) as category, now() as seen from budget_records b "
            f"join records r on r.id = b.record_id where r.user_id::text = {_ME} "
            "union all select * from (select lower(e.category), r.created_at "
            "from expense_records e join records r on r.id = e.record_id "
            f"where r.user_id::text = {_ME} order by r.created_at desc limit 200) recent"
            ") c group by category order by max(seen) desc limit 30) named), "
            "(select coalesce(json_agg(person), '[]') from ("
            "select (array_agg(l.person order by r.id))[1] as person from lending_records l "
            f"join records r on r.id = l.record_id where r.user_id::text = {_ME} "
            "and r.settled_at is null group by lower(l.person) "
            "order by max(r.created_at) desc limit 20) open)"
        )
        accounts, categories, people = cur.fetchone()
    return {"accounts": accounts, "categories": categories, "people": people}


def _entries(conn, kinds, text=None, amount=None, start=None, end=None, order="day desc",
             limit=10):
    parts, params = [], []
    for kind in kinds:
        sql = _entry_select(kind)
        if text:
            sql += " and words ilike %s escape '\\'"
            params.append(_like(text))
        if amount is not None:
            sql += " and amount = %s"
            params.append(amount)
        if start is not None:
            sql += " and day >= %s"
            params.append(start)
        if end is not None:
            sql += " and day <= %s"
            params.append(end)
        parts.append(sql)
    with conn.cursor() as cur:
        cur.execute(
            "select * from (" + " union all ".join(parts) + f") entries order by {order} limit %s",
            params + [limit],
        )
        return [{"id": row[0], "kind": row[1], "date": row[2], "amount": int(row[3]),
                 "currency": row[4].strip(), "label": row[5]} for row in cur.fetchall()]


def _entry_select(kind):
    return (f"select * from (select r.id, '{kind}'::text as kind, {_ENTRIES[kind]} "
            f"where r.user_id::text = {_ME}) as q (id, kind, day, amount, currency, label, words, cost) "
            "where true")


def _filters(category, category_clause, text, haystack):
    clauses, params = "", []
    if category:
        clauses += " and " + category_clause
        params.append(category.strip().lower())
    if text:
        clauses += f" and {haystack} ilike %s escape '\\'"
        params.append(_like(text))
    return clauses, params


def _like(text):
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"

