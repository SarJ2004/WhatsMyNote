"""Turn typed query results into a sentence.

The engine computes every number. The model only writes the words around them,
and its sentence is shown only when it quotes every number the result holds and
no number the result does not. Otherwise the plain sentence is shown instead, so
a model can make an answer read better but can never make it wrong.
"""

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal

from engine.errors import EngineError
from engine.money import SUPPORTED

_AMOUNT = re.compile(
    r"(?P<sign>[-−])?\s?(?:(?P<before>[A-Z]{3})\s)?(?P<symbol>[₹$€£¥])?\s?"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)(?:\s?(?P<after>[A-Za-z]{2,7})\b)?")
_SYMBOLS = {"₹": "INR", "$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
_CODES = {code.lower(): code for code in SUPPORTED} | {
    "rs": "INR", "rupee": "INR", "rupees": "INR", "dollar": "USD", "dollars": "USD",
    "euro": "EUR", "euros": "EUR", "pound": "GBP", "pounds": "GBP"}
_GENERIC = {"spent", "received", "you", "your", "total", "this", "last"}
_ANSWER = (
    "You answer a person's question about their own money in one or two short, friendly "
    "sentences. Use only the facts given. Quote every amount exactly as it is written in "
    "the facts. Do not add any number, total, percentage, or date that is not in the facts, "
    "and do not give advice."
)
_ADVISE = (
    "You give a person brief, practical advice about their own spending, in at most three "
    "short sentences. Ground every point in the facts given. When you mention an amount, "
    "quote it exactly as it is written in the facts. Do not add any number, total, "
    "percentage, or date that is not in the facts."
)


@dataclass(frozen=True)
class Fact:
    label: str
    value: str


@dataclass
class Answer:
    facts: list = field(default_factory=list)
    plain: str = ""
    # A query answer must quote every figure; advice may leave some out.
    exhaustive: bool = True


def phrase(question, answer, complete):
    """The model's sentence when it is faithful to the numbers, else the plain one."""
    if complete is None or not answer.facts or (answer.exhaustive and len(answer.facts) < 2):
        return answer.plain
    facts = [{"fact": fact.label, "amount": fact.value} for fact in answer.facts]
    messages = [
        {"role": "system", "content": _ANSWER if answer.exhaustive else _ADVISE},
        {"role": "user", "content": json.dumps(
            {"question": question, "facts": facts}, ensure_ascii=False)},
    ]
    try:
        sentence = complete(messages, None).strip()
    except EngineError:
        return answer.plain
    return sentence if faithful(sentence, answer, question) else answer.plain


def faithful(sentence, answer, question=""):
    """Every figure the answer holds is quoted with its sign and currency, each one
    beside the name it belongs to, and no other figure appears."""
    if not sentence or len(sentence) > 800:
        return False
    found = _amounts(sentence)
    values = [(fact, _amounts(fact.value)[0]) for fact in answer.facts if _amounts(fact.value)]
    allowed = [amount for _, amount in values]
    for text in [question] + [fact.label for fact in answer.facts]:
        allowed += [_Amount(a.value, None, a.span) for a in _amounts(text)]
    if not all(any(_same(f, a) for a in allowed) for f in found):
        return False
    if answer.exhaustive and not all(any(_same(f, a) for f in found) for _, a in values):
        return False
    return all(_beside(sentence, fact, amount, found, values) for fact, amount in values)


@dataclass(frozen=True)
class _Amount:
    value: Decimal
    currency: str | None
    span: tuple


def _amounts(text):
    found = []
    for match in _AMOUNT.finditer(text or ""):
        value = Decimal(match.group("number").replace(",", ""))
        if match.group("sign"):
            value = -value
        currency = (_SYMBOLS.get(match.group("symbol") or "")
                    or _CODES.get((match.group("before") or "").lower())
                    or _CODES.get((match.group("after") or "").lower()))
        found.append(_Amount(value, currency, match.span("number")))
    return found


def _same(found, expected):
    return found.value == expected.value and (
        found.currency is None or expected.currency is None
        or found.currency == expected.currency)


def _beside(sentence, fact, amount, found, values):
    """When the fact's name is in the sentence, the figure nearest that name must be
    the fact's own, so two people's figures cannot trade places."""
    anchor = _anchor(fact, [f for f, _ in values])
    if anchor is None:
        return True
    place = re.search(rf"\b{re.escape(anchor)}\b", sentence, re.IGNORECASE)
    if place is None:
        return True
    figures = [f for f in found if any(_same(f, a) for _, a in values)]
    if not figures:
        return True
    nearest = min(figures, key=lambda f: min(abs(f.span[0] - place.end()),
                                             abs(place.start() - f.span[1])))
    return _same(nearest, amount)


def _anchor(fact, facts):
    """A word naming this fact alone: a capitalised name, else its first word."""
    words = re.findall(r"[A-Za-z][\w'-]*", fact.label)
    named = [w for w in words if w[0].isupper()] or words[:1]
    if not named or named[0].lower() in _GENERIC:
        return None
    anchor = named[0]
    shared = sum(1 for other in facts
                 if re.search(rf"\b{re.escape(anchor)}\b", other.label, re.IGNORECASE))
    return anchor if shared == 1 else None
