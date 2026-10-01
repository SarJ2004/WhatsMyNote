"""The chat contract, end to end through HTTP, with a scripted model and no network."""

import json
import logging
from datetime import date

import psycopg2
import pytest
from fastapi.testclient import TestClient

from engine.errors import EngineError
from tests.support import ALICE, BOB

TODAY = date(2026, 9, 26)
KEY = "sk-live-do-not-echo-0123456789"
A = {"authorization": "Bearer alice-token"}
B = {"authorization": "Bearer bob-token"}
WITH_KEY = {**A, "x-model-key": KEY}


class Verifier:
    """Stands in for Supabase. Maps a token to a user id, or rejects it."""

    def __init__(self, users):
        self.users = users
        self.calls = 0

    def __call__(self, token):
        self.calls += 1
        return self.users.get(token)


class Model:
    """A scripted OpenAI-compatible model: records every call, replays answers."""

    def __init__(self):
        self.script = []
        self.calls = []

    def say(self, *answers):
        self.script.extend(answers)

    def complete_for(self, config):
        def complete(messages, schema=None):
            self.calls.append({"config": config, "messages": messages, "schema": schema})
            if not self.script:
                raise AssertionError("the model was called but nothing was scripted")
            answer = self.script.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer if isinstance(answer, str) else json.dumps(answer)
        return complete


def act(**fields):
    from engine.intent import SCHEMA

    action = {name: None for name in SCHEMA["properties"]["actions"]["items"]["properties"]}
    action.update(repayment=False, target_latest=False)
    action.update(fields)
    return action


def actions(*items):
    return {"actions": list(items)}


@pytest.fixture
def world(dsn):
    from engine.api import build_app

    verifier = Verifier({"alice-token": ALICE, "bob-token": BOB})
    model = Model()
    app = build_app(dsn=dsn, verify=verifier, complete_for=model.complete_for,
                    fetch_rate=None, today=lambda: TODAY, daily_limit=5)
    with TestClient(app) as client:
        yield client, model, verifier


def post(client, path, body, headers=A):
    return client.post(path, json=body, headers=headers)


def chat(client, message, headers=A):
    return post(client, "/chat", {"message": message}, headers)


def open_accounts(client, headers=A, **accounts):
    for name, balance in accounts.items():
        response = post(client, "/accounts", {"name": name, "currency": "INR",
                                              "opening_balance": balance}, headers)
        assert response.status_code == 200, response.text


def balances(client, headers=A):
    return {row["name"]: row["current_balance"]
            for row in client.get("/balances", headers=headers).json()["balances"]}


def test_health_is_public(world):
    client, _, _ = world
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_request_without_a_token_is_unauthenticated(world):
    client, _, _ = world
    response = client.post("/chat", json={"message": "spent 400 on dinner"})
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"
    assert "message" in response.json()


def test_a_malformed_request_without_a_token_is_unauthenticated(world):
    client, _, _ = world
    response = client.post("/chat", content=b"not json",
                           headers={"content-type": "application/json"})
    assert (response.status_code, response.json()["code"]) == (401, "unauthenticated")


def test_a_rejected_token_is_unauthenticated(world):
    client, _, _ = world
    response = chat(client, "spent 400 on dinner", {"authorization": "Bearer forged"})
    assert (response.status_code, response.json()["code"]) == (401, "unauthenticated")


def test_chat_books_an_expense_against_an_account(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    response = chat(client, "spent 400 on dinner")
    assert response.status_code == 200
    body = response.json()
    assert body["balance"] == 60000
    assert set(body) == {"reply", "balance", "confirmation", "observations"}
    assert "₹400" in body["reply"] and "₹600" in body["reply"]
    assert body["confirmation"] is None
    assert model.calls == []


def test_the_balance_is_the_account_that_was_charged(world):
    client, _, _ = world
    open_accounts(client, HDFC=100000, Cash=5000)
    body = chat(client, "spent 20 on chai from cash").json()
    assert body["balance"] == 3000
    assert balances(client) == {"HDFC": 100000, "Cash": 3000}


def test_chat_with_no_account_books_nothing(world):
    client, _, _ = world
    response = chat(client, "spent 400 on dinner")
    assert response.status_code == 422
    assert response.json()["code"] == "no_account"


def test_chat_never_charges_another_users_account(world):
    client, _, _ = world
    open_accounts(client, B, HDFC=100000)
    response = chat(client, "spent 400 on dinner")
    assert response.json()["code"] == "no_account"
    response = chat(client, "spent 400 on dinner from HDFC")
    assert response.json()["code"] == "no_account"
    assert balances(client, B) == {"HDFC": 100000}


def test_a_message_the_parser_cannot_settle_needs_a_key(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    response = chat(client, "dinner with friends came to 1200, split three ways")
    assert (response.status_code, response.json()["code"]) == (400, "no_key")
    assert balances(client) == {"HDFC": 100000}
    assert model.calls == []


def test_a_clear_booking_skips_the_model_even_with_a_key(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    assert chat(client, "spent 400 on dinner", WITH_KEY).status_code == 200
    assert model.calls == []


def test_the_model_gets_the_callers_key_endpoint_and_model(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="create", entity="expense", amount="1200", category="food",
                          note="dinner with friends")))
    headers = {**WITH_KEY, "x-model-base-url": "https://models.example/v1",
               "x-model-name": "some-model"}
    response = chat(client, "dinner with friends came to 1200", headers)
    assert response.status_code == 200, response.text
    assert response.json()["balance"] == -20000
    config = model.calls[0]["config"]
    assert (config.key, config.base_url, config.name) == (
        KEY, "https://models.example/v1", "some-model")


def test_a_missing_model_name_uses_a_current_default(world):
    from engine.intent import DEFAULT_BASE_URL, DEFAULT_MODEL

    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="create", entity="expense", amount="1200", category="food")))
    chat(client, "dinner came to 1200", WITH_KEY)
    config = model.calls[0]["config"]
    assert (config.base_url, config.name) == (DEFAULT_BASE_URL, DEFAULT_MODEL)
    assert DEFAULT_MODEL not in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")


def test_the_key_never_appears_in_a_response_or_a_log(world, caplog, capsys):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    caplog.set_level(logging.DEBUG)
    model.say(EngineError("bad_key", "the model provider rejected that key"),
              RuntimeError(f"exploded while holding {KEY}"))
    rejected = chat(client, "dinner came to 1200", WITH_KEY)
    crashed = chat(client, "dinner came to 1300", WITH_KEY)
    assert (rejected.status_code, rejected.json()["code"]) == (400, "bad_key")
    assert crashed.status_code == 500
    captured = capsys.readouterr()
    for text in (rejected.text, crashed.text, caplog.text, captured.out, captured.err):
        assert KEY not in text


def test_income_transfer_and_lending_move_the_right_accounts(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000, Cash=0)
    assert chat(client, "received 50000 salary in HDFC").json()["balance"] == 5100000
    assert chat(client, "moved 2000 from HDFC to Cash").json()["balance"] is None
    assert chat(client, "lent 500 to Ravi from cash").json()["balance"] == 150000
    body = chat(client, "lent 500 to Ravi").json()
    assert body["balance"] == 5100000 - 200000 - 50000
    model.say(actions(act(op="create", entity="lending", amount="1000", person="Ravi",
                          direction="lent", repayment=True, account="Cash")))
    assert chat(client, "Ravi returned the 1000 in cash", WITH_KEY).json()["balance"] == 250000
    assert balances(client) == {"HDFC": 4850000, "Cash": 250000}


def test_several_bookings_in_one_message_land_together(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="create", entity="expense", amount="400", category="food"),
                      act(op="create", entity="expense", amount="200", category="transport")))
    body = chat(client, "spent 400 on dinner and 200 on a cab", WITH_KEY).json()
    assert body["balance"] == 40000
    assert "₹400" in body["reply"] and "₹200" in body["reply"]


def test_a_question_is_answered_from_the_ledger_without_a_key(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "spent 400 on dinner")
    chat(client, "paid 250 for uber")
    body = chat(client, "how much did I spend on food this month").json()
    assert "₹400" in body["reply"]
    assert "₹250" not in body["reply"]
    assert body["balance"] is None
    assert model.calls == []


def test_who_owes_me_money(world):
    client, _, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "lent 500 to Ravi")
    chat(client, "Ravi paid me back 200")
    chat(client, "I borrowed 100 from Priya")
    reply = chat(client, "who owes me money").json()["reply"]
    assert "Ravi" in reply and "₹300" in reply and "Priya" not in reply


def test_am_i_over_budget(world):
    client, _, _ = world
    open_accounts(client, HDFC=100000)
    assert post(client, "/budgets", {"category": "food", "amount": 30000}).status_code == 200
    body = chat(client, "spent 400 on dinner").json()
    assert body["observations"] == [{"kind": "over_budget", "category": "food",
                                     "detail": "₹100 over its ₹300 monthly budget"}]
    reply = chat(client, "am I over budget").json()["reply"]
    assert "food" in reply.lower() and "₹400" in reply and "₹300" in reply and "₹100" in reply


def test_a_question_the_parser_cannot_read_is_judged_then_phrased(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "spent 400 on dinner")
    chat(client, "spent 900 on shoes")
    model.say(actions(act(op="query", entity="expense", metric="transactions",
                          range="this_month", order="largest")),
              "Your biggest were shoes at ₹900 and dinner at ₹400.")
    body = chat(client, "what were my biggest expenses this month?", WITH_KEY).json()
    assert body["reply"] == "Your biggest were shoes at ₹900 and dinner at ₹400."
    phrasing = json.dumps(model.calls[1]["messages"], ensure_ascii=False)
    assert "₹900" in phrasing and "₹400" in phrasing
    assert model.calls[1]["schema"] is None


def test_a_phrasing_that_invents_a_number_falls_back_to_the_plain_numbers(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "spent 400 on dinner")
    chat(client, "spent 900 on shoes")
    model.say(actions(act(op="query", entity="expense", metric="transactions",
                          range="this_month", order="largest")),
              "Shoes ₹900, dinner ₹400, ₹1,300 in all.")
    reply = chat(client, "what were my biggest expenses this month?", WITH_KEY).json()["reply"]
    assert "₹900" in reply and "₹400" in reply and "1,300" not in reply


def test_advice_is_grounded_in_the_users_numbers(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "spent 400 on dinner")
    model.say(actions(act(op="advise")), "Food is your biggest cost at ₹400; cook at home.")
    body = chat(client, "where can I cut back?", WITH_KEY).json()
    assert body["reply"] == "Food is your biggest cost at ₹400; cook at home."


def test_a_delete_asks_first_and_the_confirmation_gives_the_money_back(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "paid 250 for uber")
    model.say(actions(act(op="delete", entity="expense", target_text="uber")))
    body = chat(client, "delete the uber", WITH_KEY).json()
    assert body["confirmation"]["token"]
    assert "uber" in body["confirmation"]["summary"] and "₹250" in body["confirmation"]["summary"]
    assert balances(client) == {"HDFC": 75000}

    done = post(client, "/confirm", {"token": body["confirmation"]["token"]})
    assert done.status_code == 200, done.text
    assert done.json()["balance"] == 100000
    assert done.json()["reply"].startswith("Deleted expense uber of ₹250")
    assert set(done.json()) == {"reply", "balance", "confirmation", "observations"}

    again = post(client, "/confirm", {"token": body["confirmation"]["token"]})
    assert again.status_code == 410
    assert again.json()["code"] == "ambiguous"


def test_a_confirmation_cannot_be_used_by_another_user(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "paid 250 for uber")
    model.say(actions(act(op="delete", entity="expense", target_latest=True)))
    token = chat(client, "delete the last one", WITH_KEY).json()["confirmation"]["token"]
    stolen = post(client, "/confirm", {"token": token}, B)
    assert stolen.status_code == 410
    assert balances(client) == {"HDFC": 75000}
    assert post(client, "/confirm", {"token": token}).status_code == 200


def test_a_change_to_one_clear_entry_applies_at_once(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "paid 250 for uber")
    model.say(actions(act(op="update", entity="expense", target_text="uber", amount="300")))
    body = chat(client, "the uber was actually 300", WITH_KEY).json()
    assert body["confirmation"] is None
    assert body["balance"] == 70000


def test_a_change_that_could_mean_several_entries_asks_first(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "paid 250 for uber")
    chat(client, "paid 180 for uber")
    model.say(actions(act(op="update", entity="expense", target_text="uber", amount="300")))
    body = chat(client, "the uber was actually 300", WITH_KEY).json()
    assert body["confirmation"]["token"]
    assert "₹180" in body["confirmation"]["summary"]
    assert balances(client) == {"HDFC": 100000 - 25000 - 18000}
    done = post(client, "/confirm", {"token": body["confirmation"]["token"]}).json()
    assert done["balance"] == 100000 - 25000 - 30000
    assert done["reply"].startswith("Changed expense uber of ₹180")


def test_a_change_to_nothing_that_exists_says_so(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="delete", entity="expense", target_text="yacht")))
    body = chat(client, "delete the yacht", WITH_KEY).json()
    assert body["confirmation"] is None
    assert "yacht" in body["reply"]


def test_another_users_entries_cannot_be_changed_through_chat(world):
    client, model, _ = world
    open_accounts(client, B, HDFC=100000)
    chat(client, "paid 250 for uber", B)
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="delete", entity="expense", target_text="uber")))
    body = chat(client, "delete the uber", WITH_KEY).json()
    assert body["confirmation"] is None
    assert balances(client, B) == {"HDFC": 75000}


def test_a_clarifying_question_comes_back_as_the_reply(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="clarify", question="What was the ₹400 for?")))
    body = chat(client, "400", WITH_KEY).json()
    assert body["reply"] == "What was the ₹400 for?"
    assert balances(client) == {"HDFC": 100000}


def test_a_message_about_something_else_is_unparseable(world):
    client, model, _ = world
    model.say(actions(act(op="unsupported")))
    response = chat(client, "write me a poem", WITH_KEY)
    assert (response.status_code, response.json()["code"]) == (422, "unparseable")


def test_model_calls_stop_at_the_daily_ceiling_but_clear_bookings_do_not(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    for amount in ("101", "102", "103", "104", "105"):
        model.say(actions(act(op="create", entity="expense", amount=amount, category="food")))
        assert chat(client, f"dinner came to {amount}", WITH_KEY).status_code == 200
    refused = chat(client, "dinner came to 106", WITH_KEY)
    assert (refused.status_code, refused.json()["code"]) == (429, "limit_reached")
    assert chat(client, "spent 400 on dinner", WITH_KEY).status_code == 200


def test_budgets_are_set_and_validated(world):
    client, _, _ = world
    ok = post(client, "/budgets", {"category": "Food", "amount": 30000, "period": "weekly"})
    assert ok.status_code == 200
    assert ok.json()["budget"] == {"category": "food", "amount": 30000, "currency": "INR",
                                   "period": "weekly"}
    bad = post(client, "/budgets", {"category": "food", "amount": "lots"})
    assert (bad.status_code, bad.json()["code"]) == (422, "unparseable")


def test_a_malformed_body_gets_the_error_envelope(world):
    client, _, _ = world
    response = client.post("/chat", content=b"not json",
                           headers={**A, "content-type": "application/json"})
    assert (response.status_code, response.json()["code"]) == (422, "unparseable")
    response = post(client, "/accounts", {"name": "HDFC"})
    assert (response.status_code, response.json()["code"]) == (422, "unparseable")


def test_reads_return_the_callers_rows(world):
    client, _, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "spent 400 on dinner")
    open_accounts(client, B, Other=1)
    assert client.get("/balances", headers=A).json()["balances"][0]["name"] == "HDFC"
    spending = client.get("/spending?start=2026-09-01&end=2026-09-30", headers=A).json()
    assert spending == {"spending": [{"category": "food", "converted_minor": 40000}]}
    records = client.get("/records", headers=A).json()["records"]
    assert {r["record_type"] for r in records} == {"ACCOUNT", "EXPENSE"}
    assert client.get("/records", headers=B).json()["records"][0]["raw_text"] == "account Other"


def test_verified_token_is_reused_within_the_window(world):
    client, _, verifier = world
    for _ in range(3):
        client.get("/balances", headers=A)
    assert verifier.calls == 1


def test_verified_token_is_rechecked_after_the_window(dsn):
    from engine.api import build_app

    verifier = Verifier({"alice-token": ALICE})
    now = [1000.0]
    app = build_app(dsn=dsn, verify=verifier, fetch_rate=None, today=lambda: TODAY,
                    clock=lambda: now[0])
    with TestClient(app) as client:
        client.get("/balances", headers=A)
        now[0] += 59
        client.get("/balances", headers=A)
        now[0] += 2
        client.get("/balances", headers=A)
    assert verifier.calls == 2


def test_requests_share_a_few_pooled_connections(world, dsn):
    client, _, _ = world
    open_accounts(client, HDFC=100000)
    for _ in range(15):
        chat(client, "spent 1 on chai")
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("select count(*) from pg_stat_activity where application_name = 'whatsmynote'")
        assert cur.fetchone()[0] <= 2
    conn.close()


def test_a_foreign_expense_says_what_the_account_was_charged(dsn):
    from decimal import Decimal

    from engine.api import build_app

    app = build_app(dsn=dsn, verify={"alice-token": ALICE}.get, complete_for=Model().complete_for,
                    fetch_rate=lambda base, quote, on: Decimal("83.2"), today=lambda: TODAY)
    with TestClient(app) as client:
        open_accounts(client, HDFC=1000000)
        body = chat(client, "spent $15 on software").json()
    assert body["reply"].startswith("Booked $15 (₹1,248) for other.")
    assert body["balance"] == 1000000 - 124800


def test_an_account_can_be_renamed_through_chat(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="update", entity="account", target_text="HDFC", account="HDFC Bank")))
    chat(client, "rename HDFC to HDFC Bank", WITH_KEY)
    assert balances(client) == {"HDFC Bank": 100000}


def test_the_model_settings_never_print_the_key():
    from engine.chat import Model

    assert KEY not in repr(Model(key=KEY))


def test_advice_with_nothing_to_go_on_spends_no_model_call(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    model.say(actions(act(op="advise")))
    body = chat(client, "how can I save money?", WITH_KEY).json()
    assert len(model.calls) == 1
    assert body["reply"] == "You spent nothing this month."


def _foreign_world(dsn, currency="INR"):
    from decimal import Decimal

    from engine.api import build_app

    model = Model()
    app = build_app(dsn=dsn, verify={"alice-token": ALICE, "bob-token": BOB}.get,
                    complete_for=model.complete_for,
                    fetch_rate=lambda base, quote, on: Decimal("83"), today=lambda: TODAY)
    return app, model


def test_a_change_summary_quotes_the_entry_in_its_own_currency(dsn):
    app, model = _foreign_world(dsn)
    with TestClient(app) as client:
        open_accounts(client, HDFC=1000000)
        chat(client, "spent $10 on coffee")
        chat(client, "spent $12 on coffee")
        model.say(actions(act(op="update", entity="expense", target_text="coffee", amount="25")))
        body = chat(client, "the coffee was actually 25", WITH_KEY).json()
    assert "$12" in body["confirmation"]["summary"]
    assert "amount to $25" in body["confirmation"]["summary"]


def test_a_budget_set_through_chat_replies_in_its_own_currency(world):
    client, _, _ = world
    post(client, "/accounts", {"name": "Wise", "currency": "USD", "opening_balance": 0})
    body = chat(client, "set a monthly budget of 500 for food").json()
    assert body["reply"] == "Set a monthly food budget of $500."


def test_an_account_can_be_opened_through_chat(world):
    client, model, _ = world
    model.say(actions(act(op="create", entity="account", account="Wise", currency="USD",
                          amount="250")))
    body = chat(client, "open a Wise account in usd with 250", WITH_KEY).json()
    assert body["reply"].startswith("Opened Wise.")
    assert balances(client) == {"Wise": 25000}


def test_income_questions_are_answered(world):
    client, _, _ = world
    open_accounts(client, HDFC=0)
    chat(client, "received 50000 salary")
    assert chat(client, "how much did I earn this month").json()["reply"] == (
        "You received ₹50,000 this month.")
    assert chat(client, "how much did I spend this month").json()["reply"] == (
        "You spent nothing this month.")


def test_a_custom_range_missing_its_end_runs_to_today(world):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "spent 400 on dinner")
    model.say(actions(act(op="query", metric="spending", range="custom", start="2026-09-01")))
    reply = chat(client, "how much have I spent since the first?", WITH_KEY).json()["reply"]
    assert reply == "You spent ₹400 from 1 Sep to 26 Sep."


def test_when_the_allowance_runs_out_mid_turn_the_answer_is_plain(dsn):
    from engine.api import build_app

    model = Model()
    app = build_app(dsn=dsn, verify={"alice-token": ALICE}.get, complete_for=model.complete_for,
                    fetch_rate=None, today=lambda: TODAY, daily_limit=1)
    with TestClient(app) as client:
        open_accounts(client, HDFC=100000, Cash=100)
        model.say(actions(act(op="query", metric="balances")))
        body = chat(client, "tell me every balance", WITH_KEY).json()
    assert body["reply"] == "Cash has ₹1 and HDFC has ₹1,000."
    assert len(model.calls) == 1


@pytest.mark.parametrize("path,body", [
    ("/budgets", {"category": "food", "amount": 30000, "period": 5}),
    ("/budgets", {"category": "food", "amount": 30000, "period": "yearly"}),
    ("/budgets", {"category": "food", "amount": 30000, "currency": 5}),
    ("/budgets", {"category": "food", "amount": 30000, "currency": "BTC"}),
    ("/accounts", {"name": "Cash", "currency": 5, "opening_balance": 0}),
    ("/accounts", {"name": "Cash", "currency": "INR", "opening_balance": True}),
    ("/confirm", {}),
    ("/confirm", {"token": 7}),
    ("/chat", {"message": 7}),
    ("/chat", {"message": "  "}),
    ("/chat", {"message": "x" * 1001}),
])
def test_a_malformed_field_gets_the_error_envelope(world, path, body):
    client, _, _ = world
    response = post(client, path, body)
    assert 400 <= response.status_code < 500
    assert response.json()["code"] in ("unparseable", "unsupported_currency")


def test_a_malformed_date_gets_the_error_envelope(world):
    client, _, _ = world
    response = client.get("/spending?start=soon&end=2026-09-30", headers=A)
    assert (response.status_code, response.json()["code"]) == (422, "unparseable")


def test_an_expired_confirmation_is_gone(world, dsn):
    client, model, _ = world
    open_accounts(client, HDFC=100000)
    chat(client, "paid 250 for uber")
    model.say(actions(act(op="delete", entity="expense", target_text="uber")))
    token = chat(client, "delete the uber", WITH_KEY).json()["confirmation"]["token"]
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("update confirmations set expires_at = now() - interval '1 second'")
    conn.close()
    response = post(client, "/confirm", {"token": token})
    assert (response.status_code, response.json()["code"]) == (410, "ambiguous")
    assert balances(client) == {"HDFC": 75000}


def test_nothing_of_another_user_reaches_the_model_or_an_answer(world):
    client, model, _ = world
    open_accounts(client, B, BobBank=900000)
    chat(client, "lent 700 to Zed", B)
    chat(client, "spent 900 on a yacht", B)
    post(client, "/budgets", {"category": "yachts", "amount": 1000}, B)
    open_accounts(client, HDFC=100000)

    model.say(actions(act(op="clarify", question="What was that for?")))
    chat(client, "hmm that thing earlier", WITH_KEY)
    context = json.dumps(model.calls[0]["messages"])
    for name in ("BobBank", "Zed", "yacht"):
        assert name not in context

    for question in ("who owes me money", "what's my balance", "am I over budget",
                     "how much did I spend this month"):
        reply = chat(client, question).json()["reply"]
        for name in ("BobBank", "Zed", "yacht", "₹900", "₹700", "₹9,000"):
            assert name not in reply, (question, reply)

    model.say(actions(act(op="update", entity="expense", target_text="yacht", amount="1")))
    assert "could not find" in chat(client, "the yacht was 1", WITH_KEY).json()["reply"]
    assert balances(client, B) == {"BobBank": 900000 - 70000 - 90000}


def test_the_default_model_call_refuses_a_private_address(dsn, monkeypatch):
    import httpx

    from engine import http, intent
    from engine.api import build_app

    sent = []
    monkeypatch.setattr(http, "_client", httpx.Client(
        transport=httpx.MockTransport(lambda request: sent.append(request) or httpx.Response(500))))
    intent._PUBLIC.clear()
    app = build_app(dsn=dsn, verify={"alice-token": ALICE}.get, fetch_rate=None,
                    today=lambda: TODAY)
    with TestClient(app) as client:
        open_accounts(client, HDFC=100000)
        response = chat(client, "dinner came to 1200",
                        {**WITH_KEY, "x-model-base-url": "https://127.0.0.1/v1"})
    assert (response.status_code, response.json()["code"]) == (400, "bad_key")
    assert sent == []


def test_a_refused_chat_logs_its_code_and_reason_but_never_the_message(world, caplog, capsys):
    client, model, _ = world
    open_accounts(client, Cash=50000)
    caplog.set_level(logging.INFO)
    model.say(actions(act(op="create", entity="expense", amount="10", currency="INR",
                          category="food", note="chocolates")))
    response = chat(client, "got chocolates for 10", WITH_KEY)
    assert (response.status_code, response.json()["code"]) == (422, "unparseable")
    line = next(r.getMessage() for r in caplog.records if r.name == "whatsmynote")
    assert "POST /chat" in line and "422" in line and "unparseable" in line
    assert "the currency does not appear in the message" in line
    captured = capsys.readouterr()
    for text in (caplog.text, captured.out, captured.err):
        assert "chocolates" not in text and KEY not in text


def test_every_refused_chat_is_logged_with_its_code(world, caplog):
    client, _, _ = world
    caplog.set_level(logging.INFO)
    assert client.post("/chat", json={"message": "spent 400"}).status_code == 401
    assert post(client, "/chat", ["not", "an", "object"]).status_code == 422
    assert chat(client, "spent 400 on dinner").status_code == 422
    lines = [r.getMessage() for r in caplog.records if r.name == "whatsmynote"]
    assert len(lines) == 3
    assert "401 unauthenticated" in lines[0]
    assert "422 unparseable" in lines[1]
    assert "422 no_account" in lines[2]
