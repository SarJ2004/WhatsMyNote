"""Money values stored as integer minor units."""

import re
from dataclasses import dataclass

_AMOUNT = re.compile(r"^\$?\d{1,3}(,\d{3})*(\.\d+)?$|^\$?\d+(\.\d+)?$")


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str


def parse_amount(text: str) -> Money:
    """Parse an amount into minor units. A bare number is INR; a leading $ is USD."""
    raw = text.strip()
    if not _AMOUNT.match(raw):
        raise ValueError(f"unparseable amount: {text!r}")
    currency = "USD" if raw.startswith("$") else "INR"
    number = raw.lstrip("$").replace(",", "")
    whole, _, fraction = number.partition(".")
    minor = int(whole) * 100
    if fraction:
        minor += int(fraction[:2].ljust(2, "0"))
    return Money(minor, currency)
