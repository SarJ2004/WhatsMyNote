"""One chat turn, from a message to a reply. Channel-free: the HTTP API and the
MCP server both come through here.

A clear message is booked or answered with no model call. Anything else costs
one model call to judge intent, and a question with several figures may cost a
second to phrase the answer. Deletes, and changes that could mean more than one
entry, come back as a confirmation instead of executing.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

from engine import answers, intent, queries, usage
from engine.errors import EngineError
from engine.ledger import (
    apply, confirm, open_account, request_confirmation, set_budget, update_record,
)
from engine.money import format_money
from engine.observe import observations
from engine.parse import parse_message
from engine.phrase import phrase
from engine.rates import Converter, DbCache

MAX_MESSAGE = 1000
_ASK_FIRST = "That needs a confirmation before anything changes."


@dataclass(frozen=True)
class Model:
    """The caller's model settings for one request. Held only for that request."""

    key: str | None = field(repr=False)
    base_url: str = intent.DEFAULT_BASE_URL
    name: str = intent.DEFAULT_MODEL


class Chat:
    def __init__(self, db, complete_for, fetch_rate, today, daily_limit):
        self.db = db
        self.complete_for = complete_for
        self.fetch_rate = fetch_rate
        self.today = today
        self.daily_limit = daily_limit

    def reply(self, user, message, model):
        if not isinstance(message, str) or not message.strip():
            raise EngineError("unparseable", "send a message")
        message = message.strip()
        if len(message) > MAX_MESSAGE:
            raise EngineError("unparseable", f"keep a message under {MAX_MESSAGE} characters")
        turn = _Turn(self, user, model, self.today())
        actions = intent.from_parsed(parse_message(message, turn.today), has_model=bool(model.key))
        if actions is None:
            # Refuse a missing key or a spent allowance before reading anything.
            complete = turn.complete(required=True)
            with self.db.user(user) as conn:
                context = queries.context(conn)
            actions = intent.judge(message, turn.today, context, complete)
        return turn.carry_out(message, actions)

    def confirm(self, user, token):
        if not isinstance(token, str) or not token:
            raise EngineError("unparseable", "send the confirmation token")
        turn = _Turn(self, user, None, self.today())
        with turn.writing() as (conn, rates):
            booked = confirm(conn, token, rates)
            touched = queries.account_balances(conn, booked.accounts)
            found = observations(conn, turn.today)
        text = " ".join(filter(None, [booked.done or "Done.", _balance_sentence(touched)]))
        return _response(text, touched, found=found)


class _Turn:
    """One chat turn: who is asking, with which model, on which day."""

    def __init__(self, chat, user, model, today):
        self.chat, self.user, self.model, self.today = chat, user, model, today

    def complete(self, required):
        """The model to call, after counting the call against today's ceiling."""
        if not (self.model and self.model.key):
            if required:
                raise EngineError("no_key", "that needs a model key")
            return None
        if not usage.take(self.chat.db, self.user, self.chat.daily_limit, self.today):
            if required:
                raise EngineError("limit_reached", "today's model allowance is used up")
            return None
        return self.chat.complete_for(self.model)

    @contextmanager
    def writing(self):
        """A user transaction that may convert currencies. Rates it had to fetch are
        stored after the transaction commits, through the engine's own role."""
        with self.chat.db.user(self.user) as conn:
            cache = DbCache(conn)
            yield conn, Converter(cache, self.chat.fetch_rate)
        cache.flush(self.chat.db)

    def carry_out(self, message, actions):
        op = actions[0].op
        if op == "create":
            return self.create(message, actions)
        if op == "query":
            return self.query(message, actions)
        if op in ("update", "delete"):
            return self.change(actions[0])
        if op == "advise":
            return self.advise(message)
        return _response(actions[0].question)

    def create(self, message, actions):
        sentences, touched_ids = [], []
        with self.writing() as (conn, rates):
            for action in actions:
                sentence, accounts = _create(conn, action, message, rates, self.today)
                sentences.append(sentence)
                touched_ids += accounts
            touched = queries.account_balances(conn, list(dict.fromkeys(touched_ids)))
            found = observations(conn, self.today)
        text = " ".join(sentences + ([_balance_sentence(touched)] if touched else []))
        return _response(text, touched, found=found)

    def query(self, message, actions):
        with self.chat.db.user(self.user) as conn:
            answer = answers.combine([answers.answer(conn, a, self.today) for a in actions])
            found = observations(conn, self.today)
        complete = self.complete(required=False) if len(answer.facts) > 1 else None
        return _response(phrase(message, answer, complete), found=found)

    def advise(self, message):
        with self.chat.db.user(self.user) as conn:
            answer = answers.advice(conn, self.today)
            found = observations(conn, self.today)
        complete = self.complete(required=False) if answer.facts else None
        return _response(phrase(message, answer, complete), found=found)

    def change(self, action):
        with self.writing() as (conn, rates):
            found = queries.candidates(conn, action.entity, text=action.target_text,
                                       amount=action.target_amount, day=action.target_date)
            if not found:
                what = action.target_text or action.entity
                return _response(f"I could not find {_a(action.entity)} matching {what}. "
                                 "Nothing changed.")
            target = found[0]
            described = (f"{target['kind']} {target['label']} of "
                         f"{format_money(target['amount'], target['currency'])} on "
                         f"{target['date']:%d %b %Y}")
            if action.op == "delete":
                pending = request_confirmation(
                    conn, {"type": "delete", "record_id": target["id"],
                           "done": f"Deleted {described}."}, f"Delete {described}?")
                return _response(_ASK_FIRST, pending=pending)
            changes = _changes(action)
            if not changes:
                raise EngineError("unparseable", "say what to change")
            what = _describe(changes, target["currency"])
            if len(found) > 1 and not action.target_latest:
                pending = request_confirmation(
                    conn, {"type": "update", "record_id": target["id"], "changes": changes,
                           "done": f"Changed {described}: {what}."},
                    f"Change {described}: {what}? ({len(found)} entries match; "
                    "this is the latest.)")
                return _response(_ASK_FIRST, pending=pending)
            booked = update_record(conn, target["id"], changes, rates)
            touched = queries.account_balances(conn, booked.accounts)
            found = observations(conn, self.today)
        return _response(f"Changed {described}. " + _balance_sentence(touched), touched,
                         found=found)


def _create(conn, action, message, rates, today):
    """Book one new entry. Returns the sentence saying so and the accounts it moved."""
    amount = format_money(action.amount, action.currency or "INR") if action.amount else ""
    if action.entity == "account":
        name = action.account or action.note
        record = open_account(conn, name or "", action.currency or "INR", action.amount or 0)
        return f"Opened {name}.", [record]
    if action.entity == "budget":
        budget = queries.budget(conn, set_budget(conn, action.category, action.amount,
                                                 action.period or "monthly", action.currency))
        amount = format_money(budget["amount"], budget["currency"])
        return f"Set a {budget['period']} {budget['category']} budget of {amount}.", []
    booked = apply(conn, _booking(action, message, today), rates=rates)
    charged = booked.charged
    if charged is not None:
        if action.currency in (None, charged.currency):
            amount = format_money(charged.amount, charged.currency)
        else:
            amount += f" ({format_money(charged.amount, charged.currency)})"
    elif action.currency is None:
        currency = queries.account_balances(conn, booked.accounts[:1])[0]["currency"]
        amount = format_money(action.amount, currency)
    return _booked_sentence(action, amount), booked.accounts


def _booking(action, message, today):
    common = {"amount": action.amount, "currency": action.currency,
              "date": action.date or today, "raw_text": message}
    if action.entity == "expense":
        return {"type": "expense", "category": action.category, "note": action.note,
                "account": action.account, **common}
    if action.entity == "income":
        return {"type": "income", "source": action.category or action.note,
                "account": action.account, **common}
    if action.entity == "transfer":
        return {"type": "transfer", "source": action.account, "destination": action.to_account,
                **common}
    return {"type": "lending", "person": action.person, "direction": action.direction,
            "repayment": action.repayment, "account": action.account, "due": action.due,
            **common}


def _booked_sentence(action, amount):
    if action.entity == "expense":
        return f"Booked {amount} for {action.category or 'other'}."
    if action.entity == "income":
        return f"Added {amount}" + (f" of {action.category}." if action.category else ".")
    if action.entity == "transfer":
        return f"Moved {amount}."
    person = action.person
    if action.direction == "lent":
        return f"{person} paid you back {amount}." if action.repayment \
            else f"Noted: you lent {person} {amount}."
    return f"You paid {person} back {amount}." if action.repayment \
        else f"Noted: you borrowed {amount} from {person}."


def _changes(action):
    changes = {}
    for name in ("amount", "currency", "category", "note", "account", "to_account", "person",
                 "date", "due"):
        value = getattr(action, name)
        if value is not None:
            changes[name] = value
    if action.entity == "income" and action.category:
        changes["source"] = changes.pop("category")
    if action.entity == "account":
        name = changes.pop("account", None) or changes.pop("note", None)
        if name:
            changes["name"] = name
    if action.period:
        changes["period"] = action.period
    return changes


def _describe(changes, currency):
    parts = []
    for name, value in changes.items():
        if name == "amount":
            value = format_money(value, changes.get("currency") or currency)
        parts.append(f"{name.replace('_', ' ')} to {value}")
    return ", ".join(parts)


def _balance_sentence(touched):
    return " ".join(f"{a['name']} now has {format_money(a['balance'], a['currency'])}."
                    for a in touched)


def _response(reply, touched=(), pending=None, found=()):
    return {
        "reply": reply,
        "balance": touched[0]["balance"] if len(touched) == 1 else None,
        "confirmation": None if pending is None else {"token": pending.token,
                                                      "summary": pending.summary},
        "observations": [asdict(o) for o in found],
    }


def _a(noun):
    return ("an " if noun[0] in "aeiou" else "a ") + noun
