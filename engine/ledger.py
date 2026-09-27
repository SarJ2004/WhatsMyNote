"""The only code that writes money. One transaction per action, and the account
row is locked for the duration so two concurrent bookings cannot both succeed
against the same balance.
"""

import secrets
from datetime import date, timedelta


class LedgerError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class NeedsConfirmation:
    def __init__(self, token, summary):
        self.token = token
        self.summary = summary


def _user(conn):
    with conn.cursor() as cur:
        cur.execute("select current_setting('request.jwt.claim.sub', true)")
        value = cur.fetchone()[0]
    if not value:
        raise LedgerError("unauthenticated", "no user on this transaction")
    return value


def set_budget(conn, category, amount, period):
    user = _user(conn)
    with conn.cursor() as cur:
        cur.execute(
            "insert into records (user_id, record_type, raw_text) "
            "values (%s, 'BUDGET', %s) returning id",
            (user, f"budget {category}"),
        )
        record_id = cur.fetchone()[0]
        cur.execute(
            "insert into budget_records (record_id, category, amount, amount_minor, "
            "currency, period) values (%s, %s, %s, %s, 'INR', %s)",
            (record_id, category, amount, amount, period),
        )
    return record_id


def open_account(conn, name, currency, opening_balance, is_default=False):
    user = _user(conn)
    with conn.cursor() as cur:
        cur.execute(
            "insert into records (user_id, record_type, raw_text) "
            "values (%s, 'ACCOUNT', %s) returning id",
            (user, f"account {name}"),
        )
        record_id = cur.fetchone()[0]
        cur.execute(
            "insert into account_records (record_id, name, currency, "
            "opening_balance, current_balance, is_default) "
            "values (%s, %s, %s, %s, %s, %s)",
            (record_id, name, currency, opening_balance, opening_balance, is_default),
        )
    return record_id


def _resolve_account(cur, name):
    if name is None:
        cur.execute(
            "select a.record_id, a.name, a.currency from account_records a "
            "where a.is_default for update"
        )
    else:
        cur.execute(
            "select a.record_id, a.name, a.currency from account_records a "
            "where a.name = %s for update",
            (name,),
        )
    row = cur.fetchone()
    if row is None:
        raise LedgerError("no_account", "no account to book this against")
    return row


def apply(conn, action):
    user = _user(conn)
    kind = action["type"]

    if kind == "delete":
        token = secrets.token_urlsafe(18)
        with conn.cursor() as cur:
            cur.execute(
                "insert into confirmations (token, user_id, action, expires_at) "
                "values (%s, %s, %s::jsonb, now() + interval '10 minutes')",
                (token, user, _json(action)),
            )
        return NeedsConfirmation(token, "confirm delete")

    with conn.cursor() as cur:
        if kind == "expense":
            record_id, name, currency = _resolve_account(cur, action.get("account"))
            _book_expense(cur, user, action, record_id, name)
        elif kind == "transfer":
            _book_transfer(cur, user, action)
        else:
            raise LedgerError("unparseable", f"unknown action {kind}")
    return None


def _book_expense(cur, user, action, account_id, account_name):
    cur.execute(
        "insert into records (user_id, record_type, raw_text) "
        "values (%s, 'EXPENSE', %s) returning id",
        (user, action.get("raw_text", "expense")),
    )
    record_id = cur.fetchone()[0]
    cur.execute(
        "insert into expense_records (record_id, amount, amount_minor, currency, "
        "converted_minor, category, payment_source, expense_date) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s)",
        (record_id, action["amount"], action["amount"], action["currency"],
         action["amount"], action["category"], account_name, action["date"]),
    )
    cur.execute(
        "update account_records set current_balance = current_balance - %s "
        "where record_id = %s",
        (action["amount"], account_id),
    )


def _book_transfer(cur, user, action):
    source_id, _, _ = _resolve_account(cur, action["source"])
    dest_id, _, _ = _resolve_account(cur, action["destination"])
    cur.execute(
        "insert into records (user_id, record_type, raw_text) "
        "values (%s, 'TRANSFER', %s) returning id",
        (user, action.get("raw_text", "transfer")),
    )
    record_id = cur.fetchone()[0]
    cur.execute(
        "insert into transfer_records (record_id, amount, amount_minor, currency, "
        "source_account, destination_account, transfer_date) "
        "values (%s, %s, %s, %s, %s, %s, %s)",
        (record_id, action["amount"], action["amount"], action["currency"],
         action["source"], action["destination"], action["date"]),
    )
    cur.execute(
        "update account_records set current_balance = current_balance - %s "
        "where record_id = %s",
        (action["amount"], source_id),
    )
    cur.execute(
        "update account_records set current_balance = current_balance + %s "
        "where record_id = %s",
        (action["amount"], dest_id),
    )


def confirm(conn, token):
    user = _user(conn)
    with conn.cursor() as cur:
        cur.execute(
            "select action from confirmations where token = %s and user_id = %s "
            "and used_at is null and expires_at > now() for update",
            (token, user),
        )
        row = cur.fetchone()
        if row is None:
            raise LedgerError("ambiguous", "confirmation is invalid or expired")
        action = row[0]
        if action["type"] == "delete":
            cur.execute(
                "delete from records where id = %s and user_id = %s",
                (action["record_id"], user),
            )
        cur.execute(
            "update confirmations set used_at = now() where token = %s", (token,)
        )


def _json(action):
    import json

    def convert(value):
        if isinstance(value, date):
            return value.isoformat()
        raise TypeError

    return json.dumps(action, default=convert)
