"""Turn a message into structured fields. No model, no network."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from engine.money import parse_amount

_AMOUNT = re.compile(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?|\$?\d+(?:\.\d+)?")


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


def parse_message(text: str, today: date) -> Parsed:
    parsed = Parsed()

    amount_match = _AMOUNT.search(text)
    if amount_match:
        money = parse_amount(amount_match.group(0))
        parsed.amount = money.amount
        parsed.currency = money.currency

    if "yesterday" in text.lower():
        parsed.date = today - timedelta(days=1)

    if re.match(r"spent\b", text, re.IGNORECASE):
        parsed.record_type = "expense"
        merchant = re.search(r"\bon\s+(\S+)", text, re.IGNORECASE)
        if merchant:
            parsed.merchant = merchant.group(1)
        account = re.search(r"\bfrom\s+(\S+)", text, re.IGNORECASE)
        if account:
            parsed.account = account.group(1)

    lending = re.match(r"(\S+)\s+borrowed\b", text, re.IGNORECASE)
    if lending:
        parsed.record_type = "lending"
        parsed.person = lending.group(1)
        parsed.direction = "lent"

    return parsed
