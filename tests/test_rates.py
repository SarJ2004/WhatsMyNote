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
