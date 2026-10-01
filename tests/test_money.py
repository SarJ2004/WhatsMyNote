import pytest

from engine.money import Money, parse_amount


def test_whole_amount_parses_to_minor_units():
    assert parse_amount("400") == Money(40000, "INR")


def test_decimal_amount_parses_to_minor_units():
    assert parse_amount("4.50") == Money(450, "INR")


def test_dollar_sign_carries_usd():
    assert parse_amount("$15") == Money(1500, "USD")


def test_thousands_separator_is_ignored():
    assert parse_amount("1,250") == Money(125000, "INR")


def test_unparseable_amount_raises():
    with pytest.raises(ValueError):
        parse_amount("a lot")


def test_currency_symbols_carry_their_currency():
    assert parse_amount("€20") == Money(2000, "EUR")
    assert parse_amount("£7.5") == Money(750, "GBP")
    assert parse_amount("₹1,00,000") == Money(10000000, "INR")


def test_fractions_beyond_the_minor_unit_round_half_up():
    assert parse_amount("4.555") == Money(456, "INR")


def test_money_formats_with_its_symbol_and_grouping():
    from engine.money import format_money

    assert format_money(40000, "INR") == "₹400"
    assert format_money(10000000, "INR") == "₹1,00,000"
    assert format_money(123456, "USD") == "$1,234.56"
    assert format_money(-5050, "INR") == "-₹50.50"
    assert format_money(1000, "SEK") == "SEK 10"


def test_supported_currencies_are_the_rate_source_currencies():
    from engine.money import SUPPORTED

    assert {"INR", "USD", "EUR", "GBP", "JPY"} <= SUPPORTED
    assert "BTC" not in SUPPORTED
