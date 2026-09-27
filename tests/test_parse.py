from datetime import date

from engine.parse import parse_message


TODAY = date(2026, 9, 26)


def test_yesterday_resolves_against_the_injected_date():
    parsed = parse_message("spent 100 yesterday", TODAY)
    assert parsed.date == date(2026, 9, 25)


def test_expense_message_extracts_merchant_and_account():
    parsed = parse_message("spent 400 on dinner from HDFC", TODAY)
    assert parsed.record_type == "expense"
    assert parsed.amount == 40000
    assert parsed.merchant == "dinner"
    assert parsed.account == "HDFC"


def test_lending_message_extracts_person_and_direction():
    parsed = parse_message("John borrowed 50", TODAY)
    assert parsed.record_type == "lending"
    assert parsed.person == "John"
    assert parsed.direction == "lent"
    assert parsed.amount == 5000
