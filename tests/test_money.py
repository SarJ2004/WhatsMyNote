from datetime import date

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
