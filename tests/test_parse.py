from datetime import date

import pytest

from engine.parse import date_range, parse_message


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


def test_a_known_word_gives_the_category():
    assert parse_message("spent 400 on dinner", TODAY).category == "food"
    assert parse_message("paid 250 for uber", TODAY).category == "transport"
    assert parse_message("spent 60000 on a laptop", TODAY).category == "shopping"
    assert parse_message("spent 400 on a mystery", TODAY).category is None


def test_a_bare_number_leaves_the_currency_to_the_account():
    assert parse_message("spent 400 on dinner", TODAY).currency is None


@pytest.mark.parametrize("message,currency,amount", [
    ("spent $15 on lunch", "USD", 1500),
    ("spent 15 usd on lunch", "USD", 1500),
    ("spent rs 400 on lunch", "INR", 40000),
    ("spent 400 rupees on lunch", "INR", 40000),
    ("spent €20 on lunch", "EUR", 2000),
])
def test_an_explicit_currency_is_carried(message, currency, amount):
    parsed = parse_message(message, TODAY)
    assert (parsed.currency, parsed.amount) == (currency, amount)


def test_a_clear_expense_is_marked_clear():
    assert parse_message("spent 400 on dinner from HDFC yesterday", TODAY).clear
    assert parse_message("spent 400 on dinner and drinks", TODAY).clear
    parsed = parse_message("spent 400 on dinner from hdfc bank", TODAY)
    assert parsed.account == "hdfc bank"


@pytest.mark.parametrize("message", [
    "spent 400 on dinner and 200 on a cab",
    "change the dinner to 500",
    "delete yesterday's uber",
    "actually that was 450",
    "how much did I spend on dinner on 12 sep?",
    "paid 500 to Ramesh",
    "400",
])
def test_anything_less_than_clear_is_left_to_the_model(message):
    assert not parse_message(message, TODAY).clear


def test_income_is_recognised():
    parsed = parse_message("received 50000 salary in HDFC", TODAY)
    assert (parsed.record_type, parsed.amount, parsed.source, parsed.account) == (
        "income", 5000000, "salary", "HDFC")
    assert parsed.clear
    assert parse_message("got paid 5000", TODAY).record_type == "income"


def test_a_transfer_names_both_accounts():
    parsed = parse_message("moved 5000 from HDFC to Cash", TODAY)
    assert (parsed.record_type, parsed.account, parsed.destination) == (
        "transfer", "HDFC", "Cash")
    assert parsed.clear


@pytest.mark.parametrize("message,person,direction,repayment", [
    ("lent 500 to Ravi", "Ravi", "lent", False),
    ("lent Ravi 500", "Ravi", "lent", False),
    ("I borrowed 200 from Priya", "Priya", "borrowed", False),
    ("Ravi paid me back 500", "Ravi", "lent", True),
    ("paid Priya back 200", "Priya", "borrowed", True),
])
def test_loans_and_repayments_are_recognised(message, person, direction, repayment):
    parsed = parse_message(message, TODAY)
    assert (parsed.record_type, parsed.person, parsed.direction, parsed.repayment) == (
        "lending", person, direction, repayment)
    assert parsed.clear


def test_a_loan_can_name_the_account_it_moved():
    parsed = parse_message("lent 500 to Ravi from Cash", TODAY)
    assert (parsed.person, parsed.account, parsed.clear) == ("Ravi", "Cash", True)
    parsed = parse_message("Ravi paid me back 500 into HDFC", TODAY)
    assert (parsed.person, parsed.repayment, parsed.account) == ("Ravi", True, "HDFC")


def test_a_budget_is_recognised():
    parsed = parse_message("set a monthly budget of 5000 for food", TODAY)
    assert (parsed.record_type, parsed.amount, parsed.category, parsed.period) == (
        "budget", 500000, "food", "monthly")
    assert parsed.clear


@pytest.mark.parametrize("message,metric,extra", [
    ("what's my balance?", "balances", {}),
    ("how much did I spend on food this month", "spending",
     {"category": "food", "range": "this_month"}),
    ("how much did i spend last week?", "spending", {"range": "last_week"}),
    ("how much did I spend on shoes", "spending", {"text": "shoes", "range": "this_month"}),
    ("who owes me money", "owed", {"direction": "lent"}),
    ("who do I owe?", "owed", {"direction": "borrowed"}),
    ("am I over budget", "budgets", {}),
    ("how much did I earn last month", "income", {"range": "last_month"}),
    ("how much have i received from freelance", "income", {"text": "freelance"}),
])
def test_common_questions_are_recognised(message, metric, extra):
    parsed = parse_message(message, TODAY)
    assert parsed.record_type == "question"
    assert parsed.clear
    assert parsed.question.metric == metric
    for key, value in extra.items():
        assert getattr(parsed.question, key) == value


def test_date_ranges_resolve_against_today():
    assert date_range("this_month", TODAY) == (date(2026, 9, 1), date(2026, 9, 30))
    assert date_range("last_month", TODAY) == (date(2026, 8, 1), date(2026, 8, 31))
    assert date_range("this_week", TODAY) == (date(2026, 9, 21), date(2026, 9, 27))
    assert date_range("last_week", TODAY) == (date(2026, 9, 14), date(2026, 9, 20))
    assert date_range("yesterday", TODAY) == (date(2026, 9, 25), date(2026, 9, 25))
    assert date_range("this_year", TODAY) == (date(2026, 1, 1), date(2026, 12, 31))
    assert date_range("last_month", date(2026, 1, 15)) == (date(2025, 12, 1), date(2025, 12, 31))


@pytest.mark.parametrize("message,amount", [
    ("spent 2 lakh on flights", 20000000),
    ("spent 20 k on flights", 2000000),
    ("spent 1.5 crore on a flat", 1500000000),
    ("spent 2lakh on flights", 20000000),
])
def test_a_multiplier_word_counts_even_when_it_stands_apart(message, amount):
    assert parse_message(message, TODAY).amount == amount


def test_a_currency_named_later_in_the_message_is_carried():
    assert parse_message("spent 300 on uber in usd", TODAY).currency == "USD"
    assert parse_message("spent 300 on dinner in dollars", TODAY).currency == "USD"


def test_the_currencies_a_message_names():
    from engine.parse import currencies_in

    assert currencies_in("lunch with friends, 400") == set()
    assert currencies_in("paid $15 and 20 euros") == {"USD", "EUR"}
    assert currencies_in("try the 400 place") == set()


@pytest.mark.parametrize("message", [
    "set a budget of 5000",
    "set weekly budget 2000",
    "my budget is 5000",
])
def test_a_budget_without_a_category_is_not_clear(message):
    parsed = parse_message(message, TODAY)
    assert not (parsed.record_type == "budget" and parsed.clear)
