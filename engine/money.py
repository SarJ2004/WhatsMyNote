"""Money values stored as integer minor units, a hundredth of the major unit in
every currency, so conversion and sums never depend on per-currency exponents.
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# The currencies the rate source publishes. Anything else is refused, never guessed.
SUPPORTED = frozenset(
    "AUD BRL CAD CHF CNY CZK DKK EUR GBP HKD HUF IDR ILS INR ISK JPY KRW MXN MYR "
    "NOK NZD PHP PLN RON SEK SGD THB TRY USD ZAR".split()
)
SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY"}
_SIGNS = {code: sign for sign, code in SYMBOLS.items()}
_AMOUNT = re.compile(r"^([$€£₹¥])?(\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)$")


@dataclass(frozen=True)
class Money:
    amount: int
    currency: str


def parse_amount(text: str) -> Money:
    """Parse an amount into minor units. A bare number is INR; a symbol names its currency."""
    match = _AMOUNT.match(text.strip())
    if not match:
        raise ValueError(f"unparseable amount: {text!r}")
    currency = SYMBOLS.get(match.group(1), "INR")
    return Money(to_minor(Decimal(match.group(2).replace(",", ""))), currency)


def to_minor(value: Decimal) -> int:
    return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def format_money(minor: int, currency: str) -> str:
    """₹1,00,000 or $1,234.56: whole amounts drop the fraction, rupees group in lakhs."""
    currency = currency.strip()
    sign = "-" if minor < 0 else ""
    whole, fraction = divmod(abs(minor), 100)
    digits = _indian(whole) if currency == "INR" else f"{whole:,}"
    number = digits if fraction == 0 else f"{digits}.{fraction:02d}"
    symbol = _SIGNS.get(currency)
    return f"{sign}{symbol}{number}" if symbol else f"{sign}{currency} {number}"


def _indian(whole: int) -> str:
    text = str(whole)
    if len(text) <= 3:
        return text
    head, tail = text[:-3], text[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])
