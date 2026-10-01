"""Turn a message into structured fields. No model, no network.

The parser reads amounts, currencies, dates, accounts, people, and a category
guess. It marks a reading `clear` only when the whole message matches one of a
few unambiguous shapes; anything else is left for the model to judge.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

from engine.money import SUPPORTED, SYMBOLS, to_minor

CATEGORIES = {
    "food": "food dinner lunch breakfast brunch snack snacks coffee tea chai restaurant cafe "
            "groceries grocery swiggy zomato pizza burger meal meals biryani blinkit zepto "
            "bigbasket instamart drinks beer dessert bakery",
    "transport": "uber ola rapido cab cabs taxi auto rickshaw metro bus train fuel petrol "
                 "diesel parking toll commute",
    "travel": "flight flights hotel hotels trip vacation holiday airbnb",
    "shopping": "amazon flipkart myntra ajio meesho clothes shoes shirt jeans shopping gadget "
                "gadgets laptop electronics headphones watch furniture",
    "bills": "electricity rent wifi internet broadband phone mobile recharge bill bills water "
             "gas maintenance",
    "entertainment": "movie movies netflix spotify hotstar concert games gaming",
    "health": "medicine medicines doctor pharmacy hospital gym health dentist",
    "education": "books book course courses tuition school college",
}
_CATEGORY_OF = {word: name for name, words in CATEGORIES.items() for word in words.split()}
_INCOME_SOURCES = ("salary", "bonus", "freelance", "interest", "dividend", "refund",
                   "cashback", "stipend", "pension", "gift")
_CURRENCY_WORDS = {code.lower(): code for code in SUPPORTED} | {
    "rs": "INR", "rs.": "INR", "rupee": "INR", "rupees": "INR", "dollar": "USD",
    "dollars": "USD", "euro": "EUR", "euros": "EUR", "pound": "GBP", "pounds": "GBP",
}
_NOT_A_CATEGORY = {"a", "an", "my", "the", "set", "new", "this", "monthly", "weekly", "total"}
_PRONOUNS = {"i", "me", "you", "we", "they", "he", "she", "him", "her", "them", "it", "my"}
_EDIT = re.compile(
    r"\b(change|changed|update|edit|delete|remove|undo|cancel|wrong|actually|instead|"
    r"correct|fix|rename|not|didn't|didnt|never)\b")
_OTHER_DATES = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|last|ago|week|month|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|"
    r"june|july|august|september|october|november|december|tomorrow|morning|night)\b")
_NUMBER = re.compile(
    r"(?<![\w.,])([$€£₹¥])?\s?(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"([a-z]+\.?)?(?![\w])", re.IGNORECASE)
_MULTIPLIERS = {"k": 1000, "lakh": 10**5, "lakhs": 10**5, "lac": 10**5, "lacs": 10**5,
                "crore": 10**7, "crores": 10**7, "cr": 10**7}
_APART = re.compile(r"\s+(" + "|".join(_MULTIPLIERS) + r")\b", re.IGNORECASE)
_IN_CURRENCY = re.compile(r"\b(?:in|using)\s+([a-z]+)\b", re.IGNORECASE)
RANGES = {"today": "today", "yesterday": "yesterday", "this week": "this_week",
           "last week": "last_week", "this month": "this_month", "last month": "last_month",
           "this year": "this_year", "last year": "last_year"}
_NAMED_CURRENCY = r"(?:rs\.?|inr|usd|eur|gbp|rupees?|dollars?|euros?|pounds?)"
_CURRENCY_AROUND = rf"(?:\b{_NAMED_CURRENCY}\s*)?§(?:\s*{_NAMED_CURRENCY}\b)?"
_STOP = r"(?=\s+(?:from|using|via|yesterday|today|in|into|for|on|at|and|to)\b|$)"
_WORDS = r"[a-z][\w&'-]*(?:\s+[a-z][\w&'-]*){0,2}?"
_PERSON = r"(?P<person>[a-z][\w'-]*)"


class Number(NamedTuple):
    minor: int | None  # None for a number that is not an amount, such as a date
    currency: str | None
    span: tuple[int, int]


@dataclass
class Question:
    metric: str
    category: str | None = None
    text: str | None = None
    person: str | None = None
    direction: str | None = None
    range: str | None = None


@dataclass
class Parsed:
    amount: int | None = None
    currency: str | None = None
    date: date | None = None
    account: str | None = None
    merchant: str | None = None
    person: str | None = None
    direction: str | None = None
    record_type: str | None = None
    category: str | None = None
    source: str | None = None
    destination: str | None = None
    repayment: bool = False
    period: str | None = None
    question: Question | None = None
    clear: bool = False


def parse_message(text: str, today: date) -> Parsed:
    parsed = Parsed()
    original = " ".join(text.split())
    lowered = original.lower()

    numbers = numbers_in(original)
    amounts = [n for n in numbers if n.minor is not None]
    if amounts:
        parsed.amount, parsed.currency = amounts[0].minor, amounts[0].currency
        named = currencies_in(original)
        if parsed.currency is None and len(named) == 1:
            parsed.currency = named.pop()
    if re.search(r"\bday before yesterday\b", lowered):
        parsed.date = today - timedelta(days=2)
    elif re.search(r"\byesterday\b", lowered):
        parsed.date = today - timedelta(days=1)
    elif re.search(r"\btoday\b", lowered):
        parsed.date = today

    # One amount, replaced by a marker, lets every shape below be a plain pattern.
    # The shape is matched lower-cased; spans are read back from the same text in
    # the user's own case, so names keep the capitals they were typed with.
    single = len(numbers) == 1 and len(amounts) == 1
    source = original
    if single:
        start, end = amounts[0].span
        source = re.sub(_CURRENCY_AROUND, "§", original[:start] + "§" + original[end:],
                        flags=re.IGNORECASE)
    source = source.rstrip(" .!")
    shape = source.lower()

    if not numbers and _question(parsed, shape.rstrip("?").strip()):
        return parsed

    # Each reader returns None when the message is not its shape, or whether the
    # shape it found is complete. Clear needs both that and one plain amount.
    eligible = single and "?" not in shape and not _EDIT.search(shape) \
        and not _OTHER_DATES.search(shape)
    for reader in (_lending, _transfer, _income, _budget, _expense):
        complete = reader(parsed, shape, source)
        if complete is not None:
            parsed.clear = eligible and complete
            break
    return parsed


def date_range(name: str, today: date) -> tuple[date, date]:
    if name == "today":
        return today, today
    if name == "yesterday":
        day = today - timedelta(days=1)
        return day, day
    if name in ("this_week", "last_week"):
        monday = today - timedelta(days=today.weekday())
        if name == "last_week":
            monday -= timedelta(days=7)
        return monday, monday + timedelta(days=6)
    if name in ("this_month", "last_month"):
        year, month = today.year, today.month
        if name == "last_month":
            year, month = (year - 1, 12) if month == 1 else (year, month - 1)
        return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    if name in ("this_year", "last_year"):
        year = today.year - (name == "last_year")
        return date(year, 1, 1), date(year, 12, 31)
    return date(1900, 1, 1), date(9999, 12, 31)


def category_of(text: str | None) -> str | None:
    for word in re.findall(r"[a-z]+", (text or "").lower()):
        if word in _CATEGORY_OF:
            return _CATEGORY_OF[word]
    return None


def numbers_in(text):
    """Every number in the message. A number that is part of a date or an ordinal
    has no amount: it still makes the message less than clear, but is never booked."""
    found = []
    for match in _NUMBER.finditer(text):
        symbol, number, suffix = match.group(1), match.group(2), (match.group(3) or "").lower()
        value = Decimal(number.replace(",", ""))
        currency = SYMBOLS.get(symbol) if symbol else None
        end = match.end()
        apart = None if suffix else _APART.match(text, end)
        if apart:
            # "2 lakh" and "20 k": the multiplier belongs to the number.
            suffix, end = apart.group(1).lower(), apart.end()
        if suffix in _MULTIPLIERS:
            value *= _MULTIPLIERS[suffix]
        elif suffix in _CURRENCY_WORDS:
            currency = currency or _CURRENCY_WORDS[suffix]
        elif suffix:
            found.append(Number(None, None, match.span()))
            continue
        before = re.search(r"([a-z]+\.?)\s*$", text[:match.start()].lower())
        after = re.match(r"\s+([a-z]+)\b", text[end:].lower())
        for word in (before and before.group(1), after and after.group(1)):
            if not currency and word in _CURRENCY_WORDS and word != "try":
                currency = _CURRENCY_WORDS[word]
        found.append(Number(to_minor(value), currency, (match.start(), end)))
    return found


def currencies_in(text):
    """The currencies a message names: next to an amount, by symbol, or as "in dollars"."""
    named = {n.currency for n in numbers_in(text) if n.currency}
    for word in _IN_CURRENCY.findall(text):
        if word.lower() in _CURRENCY_WORDS and word.lower() != "try":
            named.add(_CURRENCY_WORDS[word.lower()])
    return named


def _span(source, shape, match, group):
    """The matched group as the user typed it."""
    start, end = match.span(group)
    return source[start:end] if len(source) == len(shape) else match.group(group)


def _expense(parsed, shape, source):
    if not re.match(r"(?:i\s+)?(?:spent|paid|bought|purchased)\b", shape):
        return None
    parsed.record_type = "expense"
    note = re.search(r"\b(?:on|for|at)\s+(?:a\s+|an\s+|the\s+|my\s+|some\s+)?(?P<note>"
                     + _WORDS + ")" + _STOP, shape)
    if note is None:
        note = re.match(r"(?:i\s+)?(?:bought|purchased)\s+(?:a\s+|an\s+|the\s+|some\s+)?"
                        r"(?P<note>" + _WORDS + ")" + _STOP, shape)
    if note:
        parsed.merchant = _span(source, shape, note, "note")
    account = re.search(r"\b(?:from|using|via)\s+(?:my\s+)?(?P<account>" + _WORDS + r")"
                        r"(?:\s+(?:account|card))?" + _STOP, shape)
    if account:
        parsed.account = _span(source, shape, account, "account")
    parsed.category = category_of(parsed.merchant) or category_of(shape)
    # "paid 500 to Ramesh" or "paid Priya back" may be a loan, not a purchase.
    return not re.search(r"\bback\b|\bto\s+\w+", shape)


def _income(parsed, shape, source):
    if not re.match(r"(?:i\s+)?(?:received|earned|got paid|got my salary|salary)\b", shape):
        return None
    parsed.record_type = "income"
    words = set(re.findall(r"[a-z]+", shape))
    parsed.source = next((w for w in _INCOME_SOURCES if w in words), None)
    # Money received from a person may be a loan paid back.
    sender = re.search(r"\bfrom\s+(\w+)", shape)
    account = re.search(r"\b(?:in|into|to)\s+(?:my\s+)?(?P<account>" + _WORDS + r")"
                        r"(?:\s+account)?" + _STOP, shape)
    if account:
        parsed.account = _span(source, shape, account, "account")
    return not (sender and sender.group(1) not in _INCOME_SOURCES)


def _transfer(parsed, shape, source):
    if not re.match(r"(?:i\s+)?(?:moved|move|transferred|transfer)\b", shape):
        return None
    parsed.record_type = "transfer"
    route = re.search(r"\bfrom\s+(?:my\s+)?(?P<a>" + _WORDS + r")\s+to\s+(?:my\s+)?(?P<b>"
                      + _WORDS + ")" + _STOP, shape) or \
        re.search(r"\bto\s+(?:my\s+)?(?P<b>" + _WORDS + r")\s+from\s+(?:my\s+)?(?P<a>"
                  + _WORDS + ")" + _STOP, shape)
    if route is None:
        return False
    parsed.account = _span(source, shape, route, "a")
    parsed.destination = _span(source, shape, route, "b")
    return True


_LOANS = [
    (r"(?:i\s+)?lent\s+§\s+to\s+" + _PERSON + "$", "lent", False),
    (r"(?:i\s+)?lent\s+" + _PERSON + r"\s+§$", "lent", False),
    (r"(?:i\s+)?borrowed\s+§\s+from\s+" + _PERSON + "$", "borrowed", False),
    (_PERSON + r"\s+lent\s+me\s+§$", "borrowed", False),
    (_PERSON + r"\s+borrowed\s+§(?:\s+from\s+me)?$", "lent", False),
    (_PERSON + r"\s+(?:paid\s+me\s+back|repaid\s+me|returned|paid\s+back)\s+§$", "lent", True),
    (r"(?:i\s+)?(?:paid|repaid)\s+" + _PERSON + r"\s+back\s+§$", "borrowed", True),
    (r"(?:i\s+)?(?:paid\s+back|repaid|returned)\s+§\s+to\s+" + _PERSON + "$", "borrowed", True),
]


def _lending(parsed, shape, source):
    bare = re.sub(r"\s+(?:yesterday|today|day before yesterday)$", "", shape)
    account = re.search(r"\s+(?:from|using|via|in|into)\s+(?:my\s+)?(?P<account>"
                        + _WORDS + r")(?:\s+account)?$", bare)
    # "borrowed 200 from Priya" names a person; only strip an account when the
    # message does not read as a loan without it.
    attempts = [(bare, None)] + ([(bare[:account.start()], account)] if account else [])
    for text, named in attempts:
        for pattern, direction, repayment in _LOANS:
            match = re.match(pattern, text)
            if match and match.group("person") not in _PRONOUNS:
                parsed.record_type = "lending"
                parsed.person = _span(source, shape, match, "person")
                parsed.direction = direction
                parsed.repayment = repayment
                if named:
                    parsed.account = _span(source, shape, named, "account")
                return True
    return None


def _budget(parsed, shape, source):
    period = r"(?:\s+(?:per|a|every|each)\s+(?P<per>month|week))?"
    match = re.match(r"(?:set\s+)?(?:a\s+|my\s+)?(?:(?P<pre>monthly|weekly)\s+)?budget\s+"
                     r"(?:of\s+|to\s+)?§\s+(?:for|on)\s+(?P<cat>[a-z][\w ]*?)" + period + "$",
                     shape) or \
        re.match(r"(?:set\s+)?(?:a\s+|my\s+)?(?:(?P<pre>monthly|weekly)\s+)?(?P<cat>[a-z]+)\s+"
                 r"budget\s+(?:of\s+|to\s+|at\s+|is\s+)?§" + period + "$", shape)
    if not match or match.group("cat").strip() in _NOT_A_CATEGORY:
        return None
    parsed.record_type = "budget"
    parsed.category = category_of(match.group("cat")) or match.group("cat").strip()
    if match.group("per"):
        parsed.period = "weekly" if match.group("per") == "week" else "monthly"
    else:
        parsed.period = match.group("pre") or "monthly"
    return True


def _question(parsed, shape):
    question = None
    ranges = "|".join(RANGES)
    if re.match(r"(?:what(?:'s| is| are)\s+)?(?:my\s+)?(?:total\s+|current\s+|account\s+)?"
                r"balances?$|how much (?:money )?(?:do i have|have i got)(?: left)?$|"
                r"show (?:me )?my balances?$", shape):
        question = Question("balances")
    elif match := re.match(r"how much (?:did|have) i (?:spend|spent)"
                           r"(?: (?:on|at) (?P<what>.+?))?(?: (?P<range>" + ranges + "))?$",
                           shape):
        what = match.group("what")
        category = what if what in CATEGORIES else None
        question = Question("spending", category=category,
                            text=None if category else what,
                            range=RANGES.get(match.group("range"), "this_month"))
    elif match := re.match(r"how much (?:did|have) i (?:earn|earned|receive|received|make|made)"
                           r"(?: from (?P<what>.+?))?(?: (?P<range>" + ranges + "))?$", shape):
        question = Question("income", text=match.group("what"),
                            range=RANGES.get(match.group("range"), "this_month"))
    elif re.match(r"who owes me(?: money| anything)?$", shape):
        question = Question("owed", direction="lent")
    elif re.match(r"(?:who do i owe|whom do i owe)(?: money| anything)?$", shape):
        question = Question("owed", direction="borrowed")
    elif match := re.match(r"how much does " + _PERSON + " owe me$", shape):
        question = Question("owed", person=match.group("person"), direction="lent")
    elif match := re.match(r"am i (?:over|within|under) (?:my )?budgets?"
                           r"(?: (?:on|for) (?P<what>[a-z]+))?(?: this (?:month|week))?$|"
                           r"(?:how are my budgets|budget status|how am i doing on (?:my )?"
                           r"budgets?)$", shape):
        what = match.groupdict().get("what")
        question = Question("budgets", category=what)
    if question is None:
        return False
    parsed.record_type = "question"
    parsed.question = question
    parsed.clear = True
    return True
