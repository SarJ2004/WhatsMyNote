"""Currency conversion against cached reference rates.

Rates come from an injected fetcher so tests never touch the network. The live
fetcher reads https://api.frankfurter.dev, since api.frankfurter.app now
redirects there. A failure uses the last cached rate or raises; it never guesses.
"""

from decimal import Decimal, ROUND_HALF_UP

from engine.money import Money


class RateUnavailable(Exception):
    """The rate service failed and nothing is cached."""


class UnsupportedCurrency(Exception):
    """The rate source does not carry this currency."""


def convert(amount, to_currency, on, cache, fetcher):
    if amount.currency == to_currency:
        return amount

    rate = cache.get(on, amount.currency, to_currency)
    if rate is None and fetcher is not None:
        try:
            fetched = fetcher(amount.currency, to_currency, on)
        except Exception:
            fetched = None
        if fetched is None and cache.get(on, amount.currency, to_currency) is None:
            # A fetcher that returns nothing means the currency is unsupported.
            # A fetcher that raises means the service is down.
            if _fetcher_returned_nothing(fetcher, amount.currency, to_currency, on):
                raise UnsupportedCurrency(amount.currency)
            raise RateUnavailable(amount.currency, to_currency)
        if fetched is not None:
            cache.put(on, amount.currency, to_currency, fetched)
            rate = fetched

    if rate is None:
        raise RateUnavailable(amount.currency, to_currency)

    converted = (Decimal(amount.amount) * rate).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    minor = int(converted)
    if minor == 0:
        raise ValueError("amount rounds to zero in the target currency")
    return Money(minor, to_currency)


def _fetcher_returned_nothing(fetcher, base, quote, on):
    try:
        return fetcher(base, quote, on) is None
    except Exception:
        return False
