"""MCP tools over the engine. Identity comes from the bearer token.

No tool accepts a user id. A caller who names another user's id still sees only
the rows the token's user owns, because the engine sets the transaction role
from the verified token and the queries never take a user argument.
"""

from datetime import date

import psycopg2

from engine.errors import sentence
from engine.ledger import LedgerError, apply, open_account
from engine.parse import parse_message
from engine.queries import balances as read_balances
from engine.queries import spending_by_category


class Server:
    def __init__(self, dsn, verify):
        self.dsn = dsn
        self.verify = verify

    def call(self, name, arguments):
        token = arguments.get("token", "")
        user = self.verify(token) if token else None
        if not user:
            return {"code": "unauthenticated", "message": sentence("unauthenticated")}
        try:
            with self._connect(user) as conn:
                return TOOLS[name](conn, token, arguments)
        except LedgerError as error:
            return {"code": error.code, "message": sentence(error.code)}

    def _connect(self, user):
        conn = psycopg2.connect(self.dsn)
        conn.autocommit = True
        with conn.cursor() as cur:
            # set local dies at the end of the implicit transaction on an
            # autocommit connection, so the role would not reach the query.
            cur.execute("set role authenticated")
            cur.execute(
                "select set_config('request.jwt.claim.sub', %s, false)", (user,)
            )
        return conn


def build_server(dsn, verify):
    return Server(dsn, verify)


def _today():
    return date.today().isoformat()


def log_expense(conn, token, arguments):
    amount = arguments.get("amount")
    if amount is None:
        parsed = parse_message(arguments.get("message", ""), date.today())
        amount = parsed.amount
    if amount is None:
        raise LedgerError("unparseable", "no amount")
    account = arguments.get("account")
    apply(conn, {
        "type": "expense",
        "account": account,
        "amount": amount,
        "currency": arguments.get("currency") or "INR",
        "category": arguments.get("category") or "general",
        "date": arguments.get("date") or _today(),
        "raw_text": arguments.get("message") or "expense",
    })
    return {"status": "ok"}


def log_income(conn, token, arguments):
    account = arguments.get("account")
    if account and not _account_exists(conn, account):
        open_account(
            conn, account, arguments.get("currency") or "INR",
            arguments.get("amount") or 0, is_default=True,
        )
        return {"status": "ok"}
    apply(conn, {
        "type": "income",
        "account": account,
        "amount": arguments["amount"],
        "currency": arguments.get("currency") or "INR",
        "source": arguments.get("source") or "income",
        "date": arguments.get("date") or _today(),
        "raw_text": arguments.get("message") or "income",
    })
    return {"status": "ok"}


def transfer(conn, token, arguments):
    apply(conn, {
        "type": "transfer",
        "source": arguments["source"],
        "destination": arguments["destination"],
        "amount": arguments["amount"],
        "currency": arguments.get("currency") or "INR",
        "date": arguments.get("date") or _today(),
        "raw_text": arguments.get("message") or "transfer",
    })
    return {"status": "ok"}


def balances(conn, token, arguments):
    # arguments may name a user id. It is never read.
    return read_balances(conn)


def spending(conn, token, arguments):
    start = arguments.get("start") or date.today().replace(day=1).isoformat()
    end = arguments.get("end") or date.today().isoformat()
    rows = spending_by_category(conn, start, end)
    return [{"category": category, "amount": amount} for category, amount in rows]


def ask(conn, token, arguments):
    parsed = parse_message(arguments.get("message", ""), date.today())
    if parsed.record_type != "expense" or parsed.amount is None:
        raise LedgerError("unparseable", "not a booking")
    apply(conn, {
        "type": "expense",
        "account": parsed.account,
        "amount": parsed.amount,
        "currency": parsed.currency or "INR",
        "category": parsed.merchant or "general",
        "date": parsed.date or date.today(),
        "raw_text": arguments["message"],
    })
    rows = read_balances(conn)
    return {"balances": rows}


def _account_exists(conn, name):
    with conn.cursor() as cur:
        cur.execute("select 1 from account_records where name = %s", (name,))
        return cur.fetchone() is not None


TOOLS = {
    "log_expense": log_expense,
    "log_income": log_income,
    "transfer": transfer,
    "balances": balances,
    "spending": spending,
    "ask": ask,
}
