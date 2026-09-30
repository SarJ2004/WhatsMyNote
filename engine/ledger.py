"""The only code that writes money. One transaction per action. The user's
account rows are locked, in a fixed order, for the duration, so concurrent
bookings serialise instead of both succeeding against the same balance.

Every statement filters by the user the transaction role names, as well as the
database's row-level security, so a missing role and a missing filter each fail
on their own. A change or delete reverses what the entry did to account balances
before it lands, so balances always equal the sum of the entries.
"""

import json
import secrets
from dataclasses import dataclass, field
from datetime import date

from engine.errors import EngineError
from engine.money import SUPPORTED, Money
from engine.rates import RateUnavailable, UnsupportedCurrency

MAX_MINOR = 10**15
_DETAIL = {
    "EXPENSE": "expense_records",
    "INCOME": "income_records",
    "TRANSFER": "transfer_records",
    "LENDING": "lending_records",
    "ACCOUNT": "account_records",
    "BUDGET": "budget_records",
}
_ACCOUNT_REFERENCES = (
    ("expense_records", "payment_source"),
    ("income_records", "deposit_account"),
    ("transfer_records", "source_account"),
    ("transfer_records", "destination_account"),
    ("lending_records", "account"),
)
_PERIODS = ("monthly", "weekly")  # as intent.PERIODS; the ledger imports no model code
_DATE_COLUMN = {"EXPENSE": "expense_date", "INCOME": "income_date",
                "TRANSFER": "transfer_date", "LENDING": "lending_date"}
_ACCOUNT_COLUMN = {"EXPENSE": "payment_source", "INCOME": "deposit_account",
                   "LENDING": "account"}


class LedgerError(EngineError):
    pass


@dataclass
class NeedsConfirmation:
    token: str
    summary: str


@dataclass
class Booked:
    record_id: int
    accounts: list = field(default_factory=list)
    # What a new entry moved in its account's own currency, when it moved one account.
    charged: Money | None = None
    # For a confirmed change, the sentence saying what was done.
    done: str | None = None


@dataclass(frozen=True)
class Account:
    id: int
    name: str
    currency: str
    is_default: bool


def _user(conn):
    known = getattr(conn, "user_id", None)
    if known:
        return known
    with conn.cursor() as cur:
        cur.execute("select current_setting('request.jwt.claim.sub', true)")
        value = cur.fetchone()[0]
    if not value:
        raise LedgerError("unauthenticated", "no user on this transaction")
    return value


# --- accounts and budgets -------------------------------------------------


def open_account(conn, name, currency, opening_balance, is_default=False):
    user = _user(conn)
    name = _name(name)
    currency = _currency(currency)
    _check_balance(opening_balance)
    with conn.cursor() as cur:
        accounts = _lock_accounts(cur, user)
        if _match(accounts, name):
            raise LedgerError("ambiguous", f"there is already an account named {name}")
        has_default = any(a.is_default for a in accounts)
        make_default = is_default or not has_default
        if make_default and has_default:
            _clear_default(cur, user)
        record_id = _insert_record(cur, user, "ACCOUNT", f"account {name}")
        cur.execute(
            "insert into account_records (record_id, name, currency, "
            "opening_balance, current_balance, is_default) "
            "values (%s, %s, %s, %s, %s, %s)",
            (record_id, name, currency, opening_balance, opening_balance, make_default),
        )
    return record_id


def set_budget(conn, category, amount, period="monthly", currency=None):
    """One budget per category: setting it again replaces the amount and period."""
    user = _user(conn)
    _check_amount(amount)
    category = _category(category)
    period = _period(period)
    with conn.cursor() as cur:
        _lock_accounts(cur, user)
        currency = _currency(currency or _default_currency(cur, user))
        cur.execute(
            "select b.record_id from budget_records b join records r on r.id = b.record_id "
            "where r.user_id = %s and lower(b.category) = %s for update of b",
            (user, category),
        )
        row = cur.fetchone()
        if row:
            cur.execute(
                "update budget_records set amount = %s, amount_minor = %s, currency = %s, "
                "period = %s where record_id = %s",
                (_whole(amount), amount, currency, period, row[0]),
            )
            return row[0]
        record_id = _insert_record(cur, user, "BUDGET", f"budget {category}")
        cur.execute(
            "insert into budget_records (record_id, category, amount, amount_minor, "
            "currency, period) values (%s, %s, %s, %s, %s, %s)",
            (record_id, category, _whole(amount), amount, currency, period),
        )
    return record_id


# --- bookings -------------------------------------------------------------


def apply(conn, action, rates=None):
    """Book a new entry. rates converts an amount into an account's currency."""
    user = _user(conn)
    kind = action["type"]
    booker = {
        "expense": _book_expense,
        "income": _book_income,
        "transfer": _book_transfer,
        "lending": _book_lending,
    }.get(kind)
    if booker is None:
        raise LedgerError("unparseable", f"unknown action {kind}")
    _check_amount(action.get("amount"))
    with conn.cursor() as cur:
        accounts = _lock_accounts(cur, user)
        return booker(cur, user, action, accounts, rates)


def _book_expense(cur, user, action, accounts, rates):
    account = _resolve(accounts, action.get("account"))
    day = _day(action.get("date"))
    money = Money(action["amount"], _currency(action.get("currency") or account.currency))
    converted, rate = _convert(money, account.currency, day, rates)
    record_id = _insert_record(cur, user, "EXPENSE", action.get("raw_text") or "expense")
    cur.execute(
        "insert into expense_records (record_id, amount, amount_minor, currency, "
        "converted_minor, converted_currency, fx_rate, category, merchant, "
        "payment_source, item, expense_date) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (record_id, _whole(money.amount), money.amount, money.currency, converted.amount,
         account.currency, rate, _category(action.get("category")), None,
         account.name, action.get("note"), day),
    )
    _move(cur, account.id, -converted.amount)
    return Booked(record_id, [account.id], converted)


def _book_income(cur, user, action, accounts, rates):
    account = _resolve(accounts, action.get("account"))
    day = _day(action.get("date"))
    money = Money(action["amount"], _currency(action.get("currency") or account.currency))
    converted, rate = _convert(money, account.currency, day, rates)
    record_id = _insert_record(cur, user, "INCOME", action.get("raw_text") or "income")
    cur.execute(
        "insert into income_records (record_id, amount, amount_minor, currency, "
        "converted_minor, converted_currency, fx_rate, source, deposit_account, income_date) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (record_id, _whole(money.amount), money.amount, money.currency, converted.amount,
         account.currency, rate, _label(action.get("source"), "income"), account.name, day),
    )
    _move(cur, account.id, converted.amount)
    return Booked(record_id, [account.id], converted)


def _book_transfer(cur, user, action, accounts, rates):
    """A transfer is denominated in the source account's currency."""
    source = _resolve(accounts, action.get("source"))
    destination = _resolve(accounts, action.get("destination"))
    if source.id == destination.id:
        raise LedgerError("ambiguous", "a transfer needs two different accounts")
    day = _day(action.get("date"))
    money = Money(action["amount"], _currency(action.get("currency") or source.currency))
    debit, _ = _convert(money, source.currency, day, rates)
    credit, rate = _convert(debit, destination.currency, day, rates)
    record_id = _insert_record(cur, user, "TRANSFER", action.get("raw_text") or "transfer")
    cur.execute(
        "insert into transfer_records (record_id, amount, amount_minor, currency, "
        "converted_minor, converted_currency, fx_rate, source_account, "
        "destination_account, transfer_date) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (record_id, _whole(debit.amount), debit.amount, source.currency, credit.amount,
         destination.currency, rate, source.name, destination.name, day),
    )
    _move(cur, source.id, -debit.amount)
    _move(cur, destination.id, credit.amount)
    return Booked(record_id, [source.id, destination.id])


def _book_lending(cur, user, action, accounts, rates):
    """Lent money leaves the account, borrowed money arrives, and a repayment
    reverses the direction of the loan it pays back."""
    person = _name(action.get("person"))
    direction = _direction(action.get("direction"))
    repayment = bool(action.get("repayment"))
    account = _resolve(accounts, action.get("account"))
    day = _day(action.get("date"))
    money = Money(action["amount"], _currency(action.get("currency") or account.currency))
    if repayment:
        owed = _outstanding(cur, user, person, direction, money.currency)
        if owed <= 0:
            raise LedgerError("ambiguous", f"nothing is owed between you and {person}")
        if money.amount > owed:
            raise LedgerError("ambiguous", f"that is more than is owed between you and {person}")
    converted, rate = _convert(money, account.currency, day, rates)
    record_id = _insert_record(cur, user, "LENDING", action.get("raw_text") or "lending")
    cur.execute(
        "insert into lending_records (record_id, amount, amount_minor, currency, "
        "converted_minor, converted_currency, fx_rate, person, direction, account, "
        "expected_payback_by, lending_date, is_repayment) "
        "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (record_id, _whole(money.amount), money.amount, money.currency, converted.amount,
         account.currency, rate, person, direction, account.name,
         _optional_day(action.get("due")), day, repayment),
    )
    _move(cur, account.id, _lending_sign(direction, repayment) * converted.amount)
    _settle(cur, user, person, direction, money.currency)
    return Booked(record_id, [account.id], converted)


# --- changes and deletes --------------------------------------------------


def update_record(conn, record_id, changes, rates=None):
    """Change an entry in place. Its old effect on balances is reversed first."""
    user = _user(conn)
    with conn.cursor() as cur:
        # Accounts are locked before the entry is read, so a rename or booking that
        # commits first is always seen, and every write takes locks in one order.
        accounts = _lock_accounts(cur, user)
        kind, detail = _load(cur, user, record_id)
        if kind == "ACCOUNT":
            return _update_account(cur, user, record_id, detail, changes, accounts)
        if kind == "BUDGET":
            return _update_budget(cur, user, record_id, changes)
        old = _effects(kind, detail)
        new_detail = _changed(kind, detail, changes, accounts, rates)
        columns = [c for c in new_detail if c != "record_id" and new_detail[c] != detail[c]]
        if columns:
            cur.execute(
                f"update {_DETAIL[kind]} set " + ", ".join(f"{c} = %s" for c in columns)
                + " where record_id = %s",
                [new_detail[c] for c in columns] + [record_id],
            )
        cur.execute("update records set updated_at = now() where id = %s and user_id = %s",
                    (record_id, user))
        # Net the old and new effects per account, so an edit that moves no money
        # (a new category, say) writes no balance at all.
        effects = [(name, -delta) for name, delta in old] + _effects(kind, new_detail)
        touched = _replay(cur, accounts, effects)
        if kind == "LENDING" and new_detail["person"].lower() != detail["person"].lower():
            # A loan's person names everyone's entries with them: rename them all,
            # so repayments stay against the loan they paid back.
            cur.execute(
                "update lending_records l set person = %s from records r "
                "where r.id = l.record_id and r.user_id = %s and lower(l.person) = lower(%s) "
                "and l.direction = %s and l.currency = %s",
                (new_detail["person"], user, detail["person"], detail["direction"],
                 detail["currency"]),
            )
        if kind == "LENDING":
            loans = {(d["person"].lower(), d["direction"], d["currency"].strip())
                     for d in (detail, new_detail)}
            for person, direction, currency in loans:
                _settle(cur, user, person, direction, currency)
        return Booked(record_id, touched)


def delete_record(conn, record_id):
    """Remove an entry and give back what it did to account balances."""
    user = _user(conn)
    with conn.cursor() as cur:
        accounts = _lock_accounts(cur, user)
        kind, detail = _load(cur, user, record_id)
        touched = _replay(cur, accounts, [(name, -delta) for name, delta in _effects(kind, detail)])
        cur.execute("delete from records where id = %s and user_id = %s", (record_id, user))
        if kind == "LENDING":
            _settle(cur, user, detail["person"], detail["direction"], detail["currency"])
        return Booked(record_id, touched)


def request_confirmation(conn, action, summary):
    user = _user(conn)
    token = secrets.token_urlsafe(18)
    with conn.cursor() as cur:
        cur.execute(
            "insert into confirmations (token, user_id, action, expires_at) "
            "values (%s, %s, %s::jsonb, now() + interval '10 minutes')",
            (token, user, _json(action)),
        )
    return NeedsConfirmation(token, summary)


def confirm(conn, token, rates=None):
    """Carry out a confirmed change once. The token is single-use and expires."""
    user = _user(conn)
    with conn.cursor() as cur:
        cur.execute(
            "update confirmations set used_at = now() where token = %s and user_id = %s "
            "and used_at is null and expires_at > now() returning action",
            (token, user),
        )
        row = cur.fetchone()
    if row is None:
        raise LedgerError(
            "ambiguous", "that confirmation has expired or was already used", status=410)
    action = row[0]
    if action["type"] == "delete":
        booked = delete_record(conn, action["record_id"])
    elif action["type"] == "update":
        booked = update_record(conn, action["record_id"], action["changes"], rates)
    else:
        raise LedgerError("unparseable", f"unknown confirmation {action['type']}")
    booked.done = action.get("done")
    return booked


def _update_account(cur, user, record_id, detail, changes, accounts):
    name = changes.get("name")
    if name:
        name = _name(name)
        other = _match(accounts, name)
        if other and other.id != record_id:
            raise LedgerError("ambiguous", f"there is already an account named {name}")
        cur.execute("update account_records set name = %s where record_id = %s",
                    (name, record_id))
        for table, column in _ACCOUNT_REFERENCES:
            cur.execute(
                f"update {table} t set {column} = %s from records r "
                f"where r.id = t.record_id and r.user_id = %s and lower(t.{column}) = lower(%s)",
                (name, user, detail["name"]),
            )
    if changes.get("amount") is not None:
        balance = changes["amount"]
        _check_balance(balance)
        cur.execute("update account_records set current_balance = %s where record_id = %s",
                    (balance, record_id))
    if changes.get("default"):
        _clear_default(cur, user)
        cur.execute("update account_records set is_default = true where record_id = %s",
                    (record_id,))
    return Booked(record_id, [record_id])


def _update_budget(cur, user, record_id, changes):
    if changes.get("amount") is not None:
        _check_amount(changes["amount"])
        cur.execute("update budget_records set amount = %s, amount_minor = %s "
                    "where record_id = %s", (_whole(changes["amount"]), changes["amount"],
                                             record_id))
    if changes.get("period"):
        cur.execute("update budget_records set period = %s where record_id = %s",
                    (_period(changes["period"]), record_id))
    if changes.get("category"):
        cur.execute("update budget_records set category = %s where record_id = %s",
                    (_category(changes["category"]), record_id))
    return Booked(record_id, [])


def _changed(kind, detail, changes, accounts, rates):
    """The entry as it will be after the changes, with amounts reconverted."""
    new = dict(detail)
    if changes.get("amount") is not None:
        _check_amount(changes["amount"])
        new["amount"], new["amount_minor"] = _whole(changes["amount"]), changes["amount"]
    if changes.get("currency"):
        new["currency"] = _currency(changes["currency"])
    date_column = _DATE_COLUMN[kind]
    if changes.get("date"):
        new[date_column] = _day(changes["date"])
    day = new[date_column] or date.today()

    if kind == "TRANSFER":
        source = _resolve(accounts, changes.get("account") or detail["source_account"])
        destination = _resolve(accounts, changes.get("to_account") or detail["destination_account"])
        if source.id == destination.id:
            raise LedgerError("ambiguous", "a transfer needs two different accounts")
        debit, _ = _convert(Money(new["amount_minor"], new["currency"].strip()),
                            source.currency, day, rates)
        credit, rate = _convert(debit, destination.currency, day, rates)
        new.update(amount=_whole(debit.amount), amount_minor=debit.amount,
                   currency=source.currency,
                   converted_minor=credit.amount, converted_currency=destination.currency,
                   fx_rate=rate, source_account=source.name,
                   destination_account=destination.name)
        return new

    account_column = _ACCOUNT_COLUMN[kind]
    account = _resolve(accounts, changes.get("account") or detail[account_column])
    converted, rate = _convert(Money(new["amount_minor"], new["currency"].strip()),
                               account.currency, day, rates)
    new.update(converted_minor=converted.amount, converted_currency=account.currency,
               fx_rate=rate)
    new[account_column] = account.name
    if kind == "EXPENSE":
        if changes.get("category"):
            new["category"] = _category(changes["category"])
        if changes.get("note"):
            new["item"] = changes["note"]
    elif kind == "INCOME":
        if changes.get("source"):
            new["source"] = _label(changes["source"], "income")
    elif kind == "LENDING":
        if changes.get("person"):
            new["person"] = _name(changes["person"])
        if changes.get("due"):
            new["expected_payback_by"] = _day(changes["due"])
    return new


def _effects(kind, detail):
    """What an entry did to balances: (account name, change in that account's currency)."""
    if kind == "EXPENSE":
        return [(detail["payment_source"], -detail["converted_minor"])]
    if kind == "INCOME":
        return [(detail["deposit_account"], detail["converted_minor"])]
    if kind == "TRANSFER":
        credit = detail["converted_minor"]
        return [(detail["source_account"], -detail["amount_minor"]),
                (detail["destination_account"],
                 detail["amount_minor"] if credit is None else credit)]
    if kind == "LENDING":
        sign = _lending_sign(detail["direction"], detail["is_repayment"])
        return [(detail["account"], sign * detail["converted_minor"])]
    return []


def _replay(cur, accounts, effects):
    """Apply balance changes, netted per account. Returns the accounts it moved."""
    net = {}
    for name, delta in effects:
        account = _match(accounts, name)
        if account is not None:
            net[account.id] = net.get(account.id, 0) + delta
    for account_id, delta in net.items():
        if delta:
            _move(cur, account_id, delta)
    return list(net)


def _load(cur, user, record_id):
    cur.execute(
        "select record_type::text from records where id = %s and user_id = %s for update",
        (record_id, user),
    )
    row = cur.fetchone()
    if row is None:
        raise LedgerError("ambiguous", "that entry does not exist")
    kind = row[0]
    if kind not in _DETAIL:
        raise LedgerError("unparseable", "that entry cannot be changed here")
    cur.execute(f"select * from {_DETAIL[kind]} where record_id = %s", (record_id,))
    values = cur.fetchone()
    if values is None:
        raise LedgerError("ambiguous", "that entry does not exist")
    return kind, dict(zip([d.name for d in cur.description], values, strict=True))


# --- helpers --------------------------------------------------------------


def _lock_accounts(cur, user):
    """Every account the user has, locked in id order so bookings never deadlock.
    A per-user lock comes first, so two writes that would create rows (two accounts
    of one name, say) run one after the other instead of both passing a check."""
    cur.execute(
        "select pg_advisory_xact_lock(hashtext(%(user)s)); "
        "select a.record_id, a.name, a.currency, a.is_default from account_records a "
        "join records r on r.id = a.record_id where r.user_id = %(user)s "
        "order by a.record_id for update of a",
        {"user": user},
    )
    return [Account(row[0], row[1], row[2].strip(), row[3]) for row in cur.fetchall()]


def _resolve(accounts, name):
    if name:
        account = _match(accounts, name)
        if account is None:
            # "hdfc" for "HDFC Bank": a first word is enough when only one account has it.
            wanted = name.strip().lower()
            begun = [a for a in accounts if a.name.lower().startswith(wanted + " ")]
            if len(begun) > 1:
                raise LedgerError("ambiguous", "name the account: "
                                  + ", ".join(a.name for a in begun))
            if not begun:
                raise LedgerError("no_account", f"there is no account named {name}")
            account = begun[0]
        return account
    if not accounts:
        raise LedgerError("no_account", "there is no account to book this against")
    defaults = [a for a in accounts if a.is_default]
    if len(defaults) == 1:
        return defaults[0]
    if len(accounts) == 1:
        return accounts[0]
    names = ", ".join(a.name for a in accounts)
    raise LedgerError("ambiguous", f"name the account: {names}")


def _match(accounts, name):
    if not name:
        return None
    wanted = name.strip().lower()
    for account in accounts:
        if account.name.lower() == wanted:
            return account
    return None


def _move(cur, account_id, delta):
    cur.execute(
        "update account_records set current_balance = current_balance + %s "
        "where record_id = %s",
        (delta, account_id),
    )


def _clear_default(cur, user):
    cur.execute(
        "update account_records a set is_default = false from records r "
        "where r.id = a.record_id and r.user_id = %s and a.is_default",
        (user,),
    )


def _default_currency(cur, user):
    cur.execute(
        "select a.currency from account_records a join records r on r.id = a.record_id "
        "where r.user_id = %s order by a.is_default desc, a.record_id limit 1",
        (user,),
    )
    row = cur.fetchone()
    return row[0].strip() if row else "INR"


def _insert_record(cur, user, kind, raw_text):
    cur.execute(
        "insert into records (user_id, record_type, raw_text) values (%s, %s, %s) returning id",
        (user, kind, raw_text),
    )
    return cur.fetchone()[0]


def _outstanding(cur, user, person, direction, currency):
    cur.execute(
        "select coalesce(sum(case when l.is_repayment then -l.amount_minor "
        "else l.amount_minor end), 0) from lending_records l "
        "join records r on r.id = l.record_id where r.user_id = %s "
        "and lower(l.person) = lower(%s) and l.direction = %s and l.currency = %s",
        (user, person, direction, currency),
    )
    return int(cur.fetchone()[0])


def _settle(cur, user, person, direction, currency):
    """A loan paid back in full is settled; one reopened by a change is not. Only
    rows whose state changes are written."""
    cur.execute(
        "with owed as ("
        "select coalesce(sum(case when l.is_repayment then -l.amount_minor "
        "else l.amount_minor end), 0) <= 0 as paid from lending_records l "
        "join records r on r.id = l.record_id where r.user_id = %(user)s "
        "and lower(l.person) = lower(%(person)s) and l.direction = %(direction)s "
        "and l.currency = %(currency)s) "
        "update records r set settled_at = case when owed.paid then now() end "
        "from lending_records l, owed where l.record_id = r.id and r.user_id = %(user)s "
        "and lower(l.person) = lower(%(person)s) and l.direction = %(direction)s "
        "and l.currency = %(currency)s and (r.settled_at is null) = owed.paid",
        {"user": user, "person": person, "direction": direction, "currency": currency.strip()},
    )


def _lending_sign(direction, repayment):
    lent = direction == "LENT"
    return -1 if lent != bool(repayment) else 1


def _convert(money, to_currency, on, rates):
    if money.currency == to_currency:
        return money, None
    if rates is None:
        raise LedgerError("rate_unavailable", "no rate is available for this conversion")
    try:
        return rates.convert(money, to_currency, on)
    except UnsupportedCurrency:
        raise LedgerError("unsupported_currency", f"{money.currency} is not supported") from None
    except RateUnavailable:
        raise LedgerError("rate_unavailable", "the rate service is unavailable") from None
    except ValueError:
        raise LedgerError("unparseable", "that amount is too small to convert") from None


def is_minor(value):
    """A whole number of minor units: an int, and not a bool pretending to be one."""
    return isinstance(value, int) and not isinstance(value, bool)


def _check_amount(amount):
    if not is_minor(amount) or not 0 < amount <= MAX_MINOR:
        raise LedgerError("unparseable", "an amount must be a positive number")


def _check_balance(balance):
    if not is_minor(balance) or abs(balance) > MAX_MINOR:
        raise LedgerError("unparseable", "a balance must be a whole number of minor units")


def _currency(code):
    code = (code or "").strip().upper()
    if code not in SUPPORTED:
        raise LedgerError("unsupported_currency", f"{code or 'that currency'} is not supported")
    return code


def _name(value):
    text = " ".join((value or "").split())
    if not text or len(text) > 60:
        raise LedgerError("unparseable", "a name must be between 1 and 60 characters")
    return text


def _label(value, fallback):
    text = " ".join((value or "").split())[:60]
    return text or fallback


def _category(value):
    return _label(value, "other").lower()


def _period(value):
    period = (value or "monthly").strip().lower()
    if period not in _PERIODS:
        raise LedgerError("unparseable", "a budget period is monthly or weekly")
    return period


def _direction(value):
    direction = (value or "").strip().upper()
    if direction not in ("LENT", "BORROWED"):
        raise LedgerError("unparseable", "a loan is either lent or borrowed")
    return direction


def _day(value):
    if value is None:
        return date.today()
    return _optional_day(value)


def _optional_day(value):
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise LedgerError("unparseable", "that date could not be read") from None


def _whole(minor):
    """The legacy whole-unit `amount` column; the engine reads only minor units."""
    return minor // 100


def _json(action):
    def convert(value):
        if isinstance(value, date):
            return value.isoformat()
        raise TypeError

    return json.dumps(action, default=convert)
