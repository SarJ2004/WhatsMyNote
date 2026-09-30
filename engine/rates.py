"""Currency conversion against cached reference rates.

Rates come from an injected fetcher so tests never touch the network. The live
fetcher reads https://api.frankfurter.dev, since api.frankfurter.app now
redirects there. A fetcher returns a rate, returns None for a currency the source
does not carry, or raises when the service is down. A failure uses the last
cached rate or raises; it never guesses.
"""

from decimal import ROUND_HALF_UP, Decimal

from engine import http
from engine.money import SUPPORTED, Money

_SOURCE = "https://api.frankfurter.dev/v1/"


class RateUnavailable(Exception):
    """The rate service failed and nothing is cached."""


class UnsupportedCurrency(Exception):
    """The rate source does not carry this currency."""


def convert(amount, to_currency, on, cache, fetcher):
    if amount.currency == to_currency:
        return amount
    return _at(amount, rate_for(amount.currency, to_currency, on, cache, fetcher), to_currency)


def rate_for(base, quote, on, cache, fetcher):
    for currency in (base, quote):
        if currency not in SUPPORTED:
            raise UnsupportedCurrency(currency)
    rate = cache.get(on, base, quote)
    if rate is not None:
        return rate
    if fetcher is not None:
        try:
            fetched = fetcher(base, quote, on)
        except Exception:
            pass  # the service is down: fall back to the last rate cached
        else:
            if fetched is None:
                raise UnsupportedCurrency(base)
            cache.put(on, base, quote, fetched)
            return fetched
    last = cache.last(on, base, quote)
    if last is None:
        raise RateUnavailable(base, quote)
    return last


def _at(amount, rate, to_currency):
    converted = (Decimal(amount.amount) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    minor = int(converted)
    if minor == 0:
        raise ValueError("amount rounds to zero in the target currency")
    return Money(minor, to_currency)


class Converter:
    """What the ledger converts with: the converted amount and the rate it used."""

    def __init__(self, cache, fetcher):
        self.cache = cache
        self.fetcher = fetcher

    def convert(self, amount, to_currency, on):
        if amount.currency == to_currency:
            return amount, None
        rate = rate_for(amount.currency, to_currency, on, self.cache, self.fetcher)
        return _at(amount, rate, to_currency), rate


class DbCache:
    """The rate cache in fx_rates. Reads go through the caller's own transaction.
    Users may not write rates, so new ones wait here until flush() stores them
    through the engine's own role, after the booking has committed.
    """

    def __init__(self, conn):
        self.conn = conn
        self.pending = {}

    def get(self, on, base, quote):
        if (on, base, quote) in self.pending:
            return self.pending[(on, base, quote)]
        return self._one(
            "select rate from fx_rates where rate_date = %s and base = %s and quote = %s",
            (on, base, quote),
        )

    def last(self, on, base, quote):
        return self._one(
            "select rate from fx_rates where rate_date <= %s and base = %s and quote = %s "
            "order by rate_date desc limit 1",
            (on, base, quote),
        )

    def put(self, on, base, quote, rate):
        self.pending[(on, base, quote)] = rate

    def flush(self, db):
        if not self.pending:
            return
        with db.service() as conn, conn.cursor() as cur:
            for (on, base, quote), rate in self.pending.items():
                cur.execute(
                    "insert into fx_rates (rate_date, base, quote, rate) "
                    "values (%s, %s, %s, %s) on conflict do nothing",
                    (on, base, quote, rate),
                )
        self.pending.clear()

    def _one(self, sql, params):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        return None if row is None else row[0]


def frankfurter(base, quote, on, client=None):
    response = (client or http.client()).get(
        _SOURCE + on.isoformat(), params={"base": base, "symbols": quote}, timeout=5.0
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    value = response.json().get("rates", {}).get(quote)
    return None if value is None else Decimal(str(value))
