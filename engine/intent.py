"""What the user wants done, as typed actions.

A clear message is read by the parser alone, with no model call. Anything else
takes exactly one call to an OpenAI-compatible endpoint, which returns actions
matching a fixed schema. The model never writes SQL and never sees a table: it
sees the message, today's date, and the names of the user's own accounts,
categories, and people. Every value it returns is checked here, and any amount
or currency it returns must appear in the message, so it cannot book a sum
nobody typed.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import time
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit

import httpx

from engine import http
from engine.errors import EngineError
from engine.parse import CATEGORIES, currencies_in, numbers_in

# Checked against Groq's model list when this was written: the Llama models are
# deprecated, and GPT OSS 120B is a current production model with strict schemas.
DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "openai/gpt-oss-120b"

OPS = ("create", "update", "delete", "query", "advise", "clarify", "unsupported")
ENTITIES = ("expense", "income", "transfer", "lending", "account", "budget")
METRICS = ("spending", "income", "balances", "owed", "budgets", "transactions")
DIRECTIONS = ("lent", "borrowed")
PERIODS = ("monthly", "weekly")
ORDERS = ("recent", "largest")
RANGES = ("today", "yesterday", "this_week", "last_week", "this_month", "last_month",
          "this_year", "last_year", "all", "custom")
_MAX_ACTIONS = 5
# Endpoints that refused a JSON schema, so later calls go straight to JSON mode.
_NO_SCHEMAS = set()
# Model hosts recently checked to be public, so a turn does not repeat the lookup.
_PUBLIC = {}
_PUBLIC_FOR = 300.0


@dataclass
class Action:
    op: str
    entity: str | None = None
    amount: int | None = None
    currency: str | None = None
    category: str | None = None
    note: str | None = None
    account: str | None = None
    to_account: str | None = None
    person: str | None = None
    direction: str | None = None
    repayment: bool = False
    date: date | None = None
    due: date | None = None
    period: str | None = None
    target_text: str | None = None
    target_amount: int | None = None
    target_date: date | None = None
    target_latest: bool = False
    metric: str | None = None
    range: str | None = None
    start: date | None = None
    end: date | None = None
    order: str | None = None
    question: str | None = None


def _text(description):
    return {"type": ["string", "null"], "description": description}


def _choice(values, description):
    return {"type": ["string", "null"], "enum": [*values, None], "description": description}


def _flag(description):
    # Nullable like every other field: the default model writes null for a flag
    # it has no view on, and Groq's strict mode refuses the whole answer for it.
    return {"type": ["boolean", "null"], "description": description}


_ACTION = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "op": {"type": "string", "enum": list(OPS)},
        "entity": _choice(ENTITIES, "what kind of entry"),
        "amount": _text("the number exactly as written in the message, without a symbol"),
        "currency": _text("ISO code, only if the message names a currency"),
        "category": _text("spending category, or the source of income"),
        "note": _text("the item or merchant, in a few words"),
        "account": _text("the account named in the message, or a new account's name; "
                         "for a transfer, the source"),
        "to_account": _text("for a transfer, the destination account"),
        "person": _text("the other person in a loan"),
        "direction": _choice(DIRECTIONS, "lent: they owe the user; borrowed: "
                                                   "the user owes them"),
        "repayment": _flag("true when a loan is paid back"),
        "date": _text("YYYY-MM-DD when it happened; null for today"),
        "due": _text("YYYY-MM-DD a loan should be paid back by"),
        "period": _choice(PERIODS, "a budget's period"),
        "target_text": _text("words that identify the existing entry to change or delete"),
        "target_amount": _text("the amount of the existing entry, if mentioned"),
        "target_date": _text("YYYY-MM-DD of the existing entry, if mentioned"),
        "target_latest": _flag("true when they mean the most recent one"),
        "metric": _choice(METRICS, "what a question asks about"),
        "range": _choice(RANGES, "the period a question covers"),
        "start": _text("YYYY-MM-DD, only for range custom"),
        "end": _text("YYYY-MM-DD, only for range custom"),
        "order": _choice(ORDERS, "how to list entries"),
        "question": _text("for clarify, a short question back to the person"),
    },
}
_ACTION["required"] = list(_ACTION["properties"])
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["actions"],
    "properties": {"actions": {"type": "array", "items": _ACTION}},
}

_PROMPT = """You read one message a person wrote about their own money and return, as JSON, \
what they want done. You never answer a question yourself and never compute a total.

op is one of:
- create: record something new. entity is expense, income, transfer, lending, account \
(account is the new account's name exactly as written, amount the opening balance), \
or budget.
- update: change an existing entry. Identify it with target_text, target_amount, \
target_date, or target_latest (true for "last", "latest", "that", "it"). The other fields \
hold only the new values.
- delete: remove an existing entry, identified the same way.
- query: a question about their money. metric is spending, income, balances, owed (who owes \
whom), budgets, or transactions (a list of entries; use order largest or recent). range \
defaults to this_month; use custom with start and end for other periods.
- advise: they want advice or an opinion about their money.
- clarify: it is about their money but something needed is missing; ask in question.
- unsupported: it is not about their money.

Rules:
- amount is the number exactly as the person wrote it, such as 400, 1,200, or 2k. Never \
invent an amount.
- currency is an ISO code only when they name a currency; otherwise null.
- When they mention one of their accounts, use its name from accounts. A new account \
keeps the name they give it. Otherwise account is null.
- For an expense, use a name from categories when one fits, otherwise one lowercase word \
such as """ + ", ".join(CATEGORIES) + """.
- For lending, direction is lent when they gave money and borrowed when they received it; \
repayment is true when a loan is being paid back.
- Resolve dates against today and write them as YYYY-MM-DD.
- Several new entries in one message are several create actions, and several questions are \
several query actions. Otherwise return exactly one action."""


def from_parsed(parsed, has_model):
    """Actions from the parser alone, or None when the message needs the model."""
    if not parsed.clear:
        return None
    kind = parsed.record_type
    if kind == "question":
        q = parsed.question
        return [Action("query", metric=q.metric, category=q.category, note=q.text,
                       person=q.person, direction=q.direction, range=q.range)]
    common = {"amount": parsed.amount, "currency": parsed.currency, "date": parsed.date}
    if kind == "expense":
        if parsed.category is None and has_model:
            return None
        return [Action("create", "expense", category=parsed.category or "other",
                       note=parsed.merchant, account=parsed.account, **common)]
    if kind == "income":
        return [Action("create", "income", category=parsed.source, account=parsed.account,
                       **common)]
    if kind == "transfer":
        return [Action("create", "transfer", account=parsed.account,
                       to_account=parsed.destination, **common)]
    if kind == "lending":
        return [Action("create", "lending", person=parsed.person, direction=parsed.direction,
                       repayment=parsed.repayment, account=parsed.account, **common)]
    if kind == "budget":
        return [Action("create", "budget", amount=parsed.amount, currency=parsed.currency,
                       category=parsed.category, period=parsed.period)]
    return None


def judge(message, today, context, complete):
    """One model call. Returns validated actions, or raises with a fixed code."""
    user = {
        "today": f"{today.isoformat()} ({today:%A})",
        "accounts": [{"name": a["name"], "currency": a["currency"], "default": a["default"]}
                     for a in context["accounts"]],
        "categories": context["categories"],
        "people": context["people"],
        "message": message,
    }
    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]
    raw = complete(messages, SCHEMA)
    try:
        items = json.loads(raw)["actions"]
        if not isinstance(items, list) or not 0 < len(items) <= _MAX_ACTIONS:
            raise _Invalid("wrong number of actions")
        actions = [_action(item, message, today) for item in items]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise EngineError("unparseable", "the model's answer could not be read",
                          reason=_why(error)) from None
    ops = {action.op for action in actions}
    if len(actions) > 1 and not (ops == {"create"} or ops == {"query"}):
        raise EngineError("ambiguous", "ask for one change at a time",
                          reason="several actions that are not all creates or all queries")
    if ops == {"unsupported"}:
        raise EngineError("unparseable", "that is not about your money",
                          reason="the model judged it unsupported")
    return actions


class _Invalid(ValueError):
    """A model answer that fails a check. Its text is fixed, so it may be logged."""


def _why(error):
    """Which check refused a model answer, without anything the model wrote."""
    if isinstance(error, _Invalid):
        return str(error)
    if isinstance(error, KeyError):
        return "the answer has no actions list"
    if isinstance(error, json.JSONDecodeError):
        return "the answer is not JSON"
    return f"the answer has the wrong shape ({type(error).__name__})"


def _action(item, message, today):
    if not isinstance(item, dict):
        raise _Invalid("an action is not an object")
    op = _pick(item.get("op"), OPS, required=True)
    action = Action(op)
    action.entity = _pick(item.get("entity"), ENTITIES)
    if op in ("create", "update", "delete") and action.entity is None:
        raise _Invalid("a change names what it changes")
    written = {n.minor for n in numbers_in(message) if n.minor is not None}
    action.amount = _amount(item.get("amount"), written)
    if op == "create" and action.amount is None and action.entity != "account":
        raise _Invalid("a new entry needs an amount")
    action.target_amount = _amount(item.get("target_amount"), None)
    for name in ("currency", "category", "note", "account", "to_account", "person",
                 "target_text", "question"):
        setattr(action, name, _string(item.get(name)))
    if action.currency:
        # Like an amount, a currency changes what is booked, so it must be one the
        # message itself names.
        action.currency = action.currency.upper()
        if action.currency not in currencies_in(message):
            raise _Invalid("the currency does not appear in the message")
    action.direction = _pick(item.get("direction"), DIRECTIONS)
    action.period = _pick(item.get("period"), PERIODS)
    action.metric = _pick(item.get("metric"), METRICS)
    action.range = _pick(item.get("range"), RANGES)
    action.order = _pick(item.get("order"), ORDERS)
    action.repayment = item.get("repayment") is True
    action.target_latest = item.get("target_latest") is True
    for name in ("date", "due", "target_date", "start", "end"):
        setattr(action, name, _day(item.get(name)))
    if op == "create" and action.date and action.date > today:
        raise _Invalid("an entry cannot happen in the future")
    if op == "query" and action.metric is None:
        raise _Invalid("a question names what it asks about")
    if op == "clarify" and not action.question:
        raise _Invalid("a clarification carries its question")
    if op in ("update", "delete") and not (action.target_text or action.target_amount
                                           or action.target_date or action.target_latest):
        raise _Invalid("a change says which entry it means")
    return action


def _pick(value, allowed, required=False):
    if value is None and not required:
        return None
    if value not in allowed:
        raise _Invalid("a field has a value outside its choices")
    return value


def _string(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise _Invalid("expected text")
    text = " ".join(value.split())[:300]
    return text or None


def _amount(value, written):
    """Minor units of an amount the model returned. When `written` is given, the
    amount must be one the message itself contains."""
    if value is None or value == "":
        return None
    amounts = [n.minor for n in numbers_in(str(value).replace("₹", "").replace("$", ""))
               if n.minor is not None]
    if len(amounts) != 1 or amounts[0] <= 0:
        raise _Invalid("an amount must be one positive number")
    if written is not None and amounts[0] not in written:
        raise _Invalid("the amount does not appear in the message")
    return amounts[0]


def _day(value):
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise _Invalid("a date is not YYYY-MM-DD") from None


# --- the OpenAI-compatible call ---------------------------------------------


def openai_complete(base_url, model, key, client=None, resolve=socket.getaddrinfo,
                    allow_private=False):
    """A complete(messages, schema) function for one endpoint, model, and key.

    The key is sent only as a bearer header to that endpoint. It is never logged,
    stored, or placed in an error: every failure becomes a fixed code whose
    message is written here, not copied from the endpoint.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    endpoint = (url, model)
    client = client or http.client()

    def complete(messages, schema=None):
        _check_address(base_url, resolve, allow_private)
        body = {"model": model, "messages": messages}
        if "gpt-oss" in model:
            body.update(reasoning_effort="low", max_completion_tokens=2048)
        if schema is not None and endpoint in _NO_SCHEMAS:
            _plain_json(body, messages, schema)
        elif schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "actions", "strict": True, "schema": schema}}
        response = _post(client, url, key, body)
        if response.status_code == 400 and schema is not None and endpoint not in _NO_SCHEMAS:
            if _missed_schema(response):
                # The endpoint takes schemas; this one answer did not fit. That
                # says nothing about the next call, so nothing is remembered.
                raise EngineError("unparseable", "the model's answer could not be read",
                                  status=502, reason="the model's answer did not match the schema")
            # Not every endpoint takes a JSON schema. Plain JSON mode is checked
            # just as strictly here, so fall back to it for this endpoint.
            _NO_SCHEMAS.add(endpoint)
            _plain_json(body, messages, schema)
            response = _post(client, url, key, body)
        _refuse(response.status_code)
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            content = None
        if not isinstance(content, str):
            raise EngineError("unparseable", "the model's answer could not be read", status=502)
        return content

    return complete


def _plain_json(body, messages, schema):
    """Ask for plain JSON, which carries no schema, so the schema goes in the prompt:
    without it the model does not know the shape its answer must take."""
    body["response_format"] = {"type": "json_object"}
    body["messages"] = [*messages, {
        "role": "system",
        "content": "Answer with one JSON object that matches this JSON schema exactly, "
                   "with every property present:\n" + json.dumps(schema)}]


def _missed_schema(response):
    """Whether a 400 is the endpoint checking one answer against the schema, as
    Groq's strict mode does, rather than refusing schemas altogether."""
    try:
        error = response.json().get("error") or {}
        return error.get("code") == "json_validate_failed"
    except (ValueError, AttributeError):
        return False


def _post(client, url, key, body):
    try:
        return client.post(url, json=body, headers={"authorization": f"Bearer {key}"},
                           timeout=httpx.Timeout(30.0, connect=5.0))
    except httpx.HTTPError as error:
        raise EngineError("unparseable", "the model did not answer, so nothing was changed",
                          status=502, reason=f"the call failed ({type(error).__name__})") from None


def _refuse(status):
    if status < 400:
        return
    reason = f"the model provider answered {status}"
    if status in (401, 403):
        raise EngineError("bad_key", "the model provider rejected that key", reason=reason)
    if status == 404:
        raise EngineError("bad_key", "the model provider does not know that model or address",
                          reason=reason)
    if status == 429:
        raise EngineError("limit_reached", "the model provider is limiting this key; "
                                           "try again shortly", reason=reason)
    raise EngineError("unparseable", "the model did not answer, so nothing was changed",
                      status=502, reason=reason)


def _check_address(base_url, resolve, allow_private):
    """A model address is a public https host, so a request can never be pointed
    at the service's own network. Self-hosters may allow private hosts."""
    parts = urlsplit(base_url)
    if parts.username or parts.password or not parts.hostname:
        raise EngineError("bad_key", "that model address is not valid")
    if allow_private:
        return
    if parts.scheme != "https":
        raise EngineError("bad_key", "a model address must use https")
    now = time.monotonic()
    if now - _PUBLIC.get(parts.hostname, -_PUBLIC_FOR) < _PUBLIC_FOR:
        return
    try:
        addresses = {info[4][0] for info in resolve(parts.hostname, parts.port or 443,
                                                    proto=socket.IPPROTO_TCP)}
    except OSError:
        raise EngineError("bad_key", "that model address could not be found") from None
    if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
        raise EngineError("bad_key", "a model address must be a public host")
    _PUBLIC[parts.hostname] = now

