from datetime import date
from decimal import Decimal

import pytest

from engine.money import Money
from engine.rates import RateUnavailable, UnsupportedCurrency, convert


class Cache:
    def __init__(self, rates=None):
        self.rates = dict(rates or {})
        self.writes = []

    def get(self, on, base, quote):
        return self.rates.get((on, base, quote))

    def last(self, on, base, quote):
        earlier = [day for (day, b, q) in self.rates if b == base and q == quote and day <= on]
        return self.rates[(max(earlier), base, quote)] if earlier else None

    def put(self, on, base, quote, rate):
        self.rates[(on, base, quote)] = rate
        self.writes.append((on, base, quote, rate))


TODAY = date(2026, 9, 26)


def test_same_currency_never_touches_the_cache():
    cache = Cache()
    result = convert(Money(1500, "USD"), "USD", TODAY, cache, fetcher=None)
    assert result == Money(1500, "USD")
    assert cache.writes == []


def test_exact_half_rounds_away_from_zero():
    cache = Cache({(TODAY, "USD", "INR"): Decimal("83.335")})
    # 100 minor units * 83.335 = 8333.5, which is exactly half a minor unit.
    result = convert(Money(100, "USD"), "INR", TODAY, cache, fetcher=None)
    assert result.amount == 8334


def test_repeating_rate_rounds_to_nearest_minor_unit():
    cache = Cache({(TODAY, "USD", "INR"): Decimal("83.333333")})
    result = convert(Money(300, "USD"), "INR", TODAY, cache, fetcher=None)
    assert result.amount == 25000


def test_sub_unit_amount_rounds_to_zero_and_is_rejected():
    cache = Cache({(TODAY, "INR", "USD"): Decimal("0.001")})
    with pytest.raises(ValueError):
        convert(Money(1, "INR"), "USD", TODAY, cache, fetcher=None)


def test_large_amount_does_not_overflow():
    cache = Cache({(TODAY, "USD", "INR"): Decimal("83.5")})
    result = convert(Money(10**12, "USD"), "INR", TODAY, cache, fetcher=None)
    assert result.amount == 835 * 10**11


def test_cache_miss_fetches_once_and_stores():
    calls = []

    def fetcher(base, quote, on):
        calls.append((base, quote, on))
        return Decimal("83.0")

    cache = Cache()
    result = convert(Money(100, "USD"), "INR", TODAY, cache, fetcher=fetcher)
    assert result.amount == 8300
    assert calls == [("USD", "INR", TODAY)]
    assert cache.writes == [(TODAY, "USD", "INR", Decimal("83.0"))]


def test_fetcher_failure_uses_cached_rate():
    cache = Cache({(TODAY, "USD", "INR"): Decimal("80")})

    def fetcher(base, quote, on):
        raise RuntimeError("down")

    result = convert(Money(100, "USD"), "INR", TODAY, cache, fetcher=fetcher)
    assert result.amount == 8000


def test_fetcher_failure_with_nothing_cached_raises():
    def fetcher(base, quote, on):
        raise RuntimeError("down")

    with pytest.raises(RateUnavailable):
        convert(Money(100, "USD"), "INR", TODAY, Cache(), fetcher=fetcher)


def test_usd_against_inr_converts_with_cached_rate():
    cache = Cache({(TODAY, "USD", "INR"): Decimal("83.2")})
    result = convert(Money(1500, "USD"), "INR", TODAY, cache, fetcher=None)
    assert result == Money(124800, "INR")


def test_unsupported_currency_raises():
    def fetcher(base, quote, on):
        return None

    with pytest.raises(UnsupportedCurrency):
        convert(Money(100, "XYZ"), "INR", TODAY, Cache(), fetcher=fetcher)


def test_fetcher_failure_uses_the_last_cached_rate():
    cache = Cache({(date(2026, 9, 20), "USD", "INR"): Decimal("82")})

    def fetcher(base, quote, on):
        raise RuntimeError("down")

    result = convert(Money(100, "USD"), "INR", TODAY, cache, fetcher=fetcher)
    assert result.amount == 8200


def test_an_unsupported_currency_never_reaches_the_fetcher():
    calls = []

    def fetcher(base, quote, on):
        calls.append(base)
        return Decimal("1")

    with pytest.raises(UnsupportedCurrency):
        convert(Money(100, "BTC"), "INR", TODAY, Cache(), fetcher=fetcher)
    assert calls == []


def test_the_converter_reports_the_rate_it_used():
    from engine.rates import Converter

    converter = Converter(Cache({(TODAY, "USD", "INR"): Decimal("83.2")}), fetcher=None)
    assert converter.convert(Money(1500, "USD"), "INR", TODAY) == (
        Money(124800, "INR"), Decimal("83.2"))
    assert converter.convert(Money(1500, "INR"), "INR", TODAY) == (Money(1500, "INR"), None)


def test_the_database_cache_reads_rates_and_writes_only_when_flushed(dsn):
    from engine.db import Database
    from engine.rates import DbCache
    from tests.support import ALICE

    db = Database(dsn, size=2)
    try:
        with db.user(ALICE) as conn:
            cache = DbCache(conn)
            cache.put(TODAY, "USD", "INR", Decimal("83.5"))
            assert cache.get(TODAY, "USD", "INR") == Decimal("83.5")
        cache.flush(db)
        with db.user(ALICE) as conn:
            fresh = DbCache(conn)
            assert fresh.get(TODAY, "USD", "INR") == Decimal("83.5")
            assert fresh.last(date(2026, 9, 30), "USD", "INR") == Decimal("83.5")
            assert fresh.get(date(2026, 9, 30), "USD", "INR") is None
    finally:
        db.close()


def _transport(status, body):
    import httpx

    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(status, json=body)

    return httpx.Client(transport=httpx.MockTransport(handler)), seen


def test_the_live_fetcher_reads_the_rate_for_the_day():
    from engine.rates import frankfurter

    client, seen = _transport(200, {"base": "USD", "date": "2026-09-25", "rates": {"INR": 95.82}})
    assert frankfurter("USD", "INR", TODAY, client=client) == Decimal("95.82")
    assert seen == ["https://api.frankfurter.dev/v1/2026-09-26?base=USD&symbols=INR"]


def test_the_live_fetcher_returns_nothing_for_an_unknown_currency():
    from engine.rates import frankfurter

    client, _ = _transport(404, {"message": "not found"})
    assert frankfurter("USD", "AED", TODAY, client=client) is None


def test_the_live_fetcher_raises_when_the_service_fails():
    from engine.rates import frankfurter

    import httpx

    client, _ = _transport(502, {"message": "bad gateway"})
    with pytest.raises(httpx.HTTPStatusError):
        frankfurter("USD", "INR", TODAY, client=client)
