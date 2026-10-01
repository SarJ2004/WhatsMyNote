import json
import re
from datetime import date
from pathlib import Path

import httpx
import jsonschema
import pytest

from engine import intent
from engine.errors import EngineError
from engine.intent import Action, from_parsed, judge, openai_complete
from engine.parse import parse_message

RECORDED = json.loads((Path(__file__).parent / "recordings" / "intent.json").read_text())
TODAY = date.fromisoformat(RECORDED["today"])
CONTEXT = {"accounts": [{"name": "HDFC", "currency": "INR", "default": True},
                        {"name": "Cash", "currency": "INR", "default": False}],
           "categories": ["food", "transport"], "people": ["Ravi"]}
TABLES = re.compile(r"\b(records|expense_records|account_records|budget_records|income_records|"
                    r"transfer_records|lending_records|fx_rates|confirmations|model_usage)\b")
SQL = re.compile(r"\bselect\b.+\bfrom\b|\binsert\s+into\b|\bdelete\s+from\b|\bupdate\s+\w+\s+set\b",
                 re.IGNORECASE | re.DOTALL)


@pytest.fixture(autouse=True)
def fresh_endpoint_memory():
    """What the engine learns about endpoints lasts for the process; tests start clean."""
    intent._PUBLIC.clear()
    intent._NO_SCHEMAS.clear()


def blank(**fields):
    action = {name: None for name in intent.SCHEMA["properties"]["actions"]["items"]["properties"]}
    action.update(repayment=False, target_latest=False)
    action.update(fields)
    return action


def stub(content, calls=None):
    def complete(messages, schema=None):
        if calls is not None:
            calls.append((messages, schema))
        return content if isinstance(content, str) else json.dumps(content)
    return complete


@pytest.mark.parametrize("case", RECORDED["cases"], ids=[c["message"] for c in RECORDED["cases"]])
def test_a_recorded_model_response_becomes_the_matching_actions(case):
    # Groq's strict mode refuses an answer that misses the schema, so a recorded
    # answer must fit it before the engine ever reads it.
    jsonschema.validate(case["content"], intent.SCHEMA)
    actions = judge(case["message"], TODAY, CONTEXT, stub(case["content"]))
    assert len(actions) == len(case["expect"])
    for action, expected in zip(actions, case["expect"], strict=True):
        for key, value in expected.items():
            got = getattr(action, key)
            assert (got.isoformat() if isinstance(got, date) else got) == value, key


def test_the_prompt_holds_no_table_name_and_no_sql():
    calls = []
    judge("spent 400 on dinner and 200 on a cab", TODAY, CONTEXT,
          stub({"actions": [blank(op="create", entity="expense", amount="400")]}, calls))
    messages, schema = calls[0]
    text = json.dumps(messages) + json.dumps(schema)
    assert not TABLES.search(text)
    assert not SQL.search(text)
    assert "HDFC" in text and "2026-09-26" in text


def test_a_response_that_is_not_json_is_refused():
    with pytest.raises(EngineError) as caught:
        judge("spent 400 on dinner and 200 on a cab", TODAY, CONTEXT, stub("Sure! I booked it."))
    assert caught.value.code == "unparseable"


def test_a_response_with_the_wrong_shape_is_refused():
    with pytest.raises(EngineError) as caught:
        judge("spent 400", TODAY, CONTEXT, stub({"actions": [{"op": "drop_tables"}]}))
    assert caught.value.code == "unparseable"


def test_an_amount_the_message_never_mentions_is_refused():
    with pytest.raises(EngineError) as caught:
        judge("spent some money on dinner", TODAY, CONTEXT,
              stub({"actions": [blank(op="create", entity="expense", amount="4000")]}))
    assert caught.value.code == "unparseable"


def test_a_date_in_the_future_is_refused_for_a_booking():
    with pytest.raises(EngineError):
        judge("spent 400 on dinner on friday", TODAY, CONTEXT,
              stub({"actions": [blank(op="create", entity="expense", amount="400",
                                      date="2026-10-02")]}))


def test_mixed_operations_in_one_message_are_refused():
    with pytest.raises(EngineError) as caught:
        judge("delete the uber and spent 400 on dinner", TODAY, CONTEXT, stub({"actions": [
            blank(op="delete", entity="expense", target_text="uber"),
            blank(op="create", entity="expense", amount="400")]}))
    assert caught.value.code == "ambiguous"


def test_a_message_about_something_else_is_unparseable():
    with pytest.raises(EngineError) as caught:
        judge("what's the weather", TODAY, CONTEXT, stub({"actions": [blank(op="unsupported")]}))
    assert caught.value.code == "unparseable"


def test_a_clarifying_question_is_passed_back():
    actions = judge("spent 400", TODAY, CONTEXT, stub({"actions": [
        blank(op="clarify", question="What was the ₹400 for?")]}))
    assert actions[0].op == "clarify" and actions[0].question == "What was the ₹400 for?"


def test_a_clear_booking_needs_no_model():
    parsed = parse_message("spent 400 on dinner from HDFC", TODAY)
    [action] = from_parsed(parsed, has_model=True)
    assert (action.op, action.entity, action.amount, action.category, action.account) == (
        "create", "expense", 40000, "food", "HDFC")


def test_an_unknown_category_goes_to_the_model_when_there_is_one():
    parsed = parse_message("spent 400 on a mystery", TODAY)
    assert from_parsed(parsed, has_model=True) is None
    [action] = from_parsed(parsed, has_model=False)
    assert (action.category, action.note) == ("other", "mystery")


def test_a_common_question_needs_no_model():
    [action] = from_parsed(parse_message("who owes me money", TODAY), has_model=True)
    assert (action.op, action.metric, action.direction) == ("query", "owed", "lent")


def test_an_unclear_message_goes_to_the_model():
    assert from_parsed(parse_message("fix the dinner one", TODAY), has_model=True) is None


# --- the OpenAI-compatible call -------------------------------------------------


def transport(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def public(host, port, **kwargs):
    return [(2, 1, 6, "", ("104.18.0.1", port))]


def completion(content):
    return {"choices": [{"message": {"role": "assistant", "content": content}}]}


def test_the_call_sends_the_key_model_and_schema_to_the_endpoint():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=completion('{"actions": []}'))

    complete = openai_complete("https://models.example/v1", "some-model", "sk-secret",
                               client=transport(handler), resolve=public)
    assert complete([{"role": "user", "content": "hi"}], intent.SCHEMA) == '{"actions": []}'
    request = seen[0]
    body = json.loads(request.content)
    assert str(request.url) == "https://models.example/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer sk-secret"
    assert body["model"] == "some-model"
    assert body["response_format"]["type"] == "json_schema"


def test_the_default_model_is_asked_to_reason_briefly():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=completion("ok"))

    openai_complete(intent.DEFAULT_BASE_URL, intent.DEFAULT_MODEL, "k",
                    client=transport(handler), resolve=public)([], None)
    assert seen[0]["reasoning_effort"] == "low"
    assert intent.DEFAULT_MODEL not in ("llama-3.3-70b-versatile", "llama-3.1-8b-instant")


def test_an_endpoint_without_schemas_is_retried_once_with_plain_json():
    formats = []

    def handler(request):
        formats.append(json.loads(request.content)["response_format"]["type"])
        if formats[-1] == "json_schema":
            return httpx.Response(400, json={"error": {"message": "response_format"}})
        return httpx.Response(200, json=completion('{"actions": []}'))

    complete = openai_complete("https://other.example/v1", "m", "k", client=transport(handler),
                               resolve=public)
    complete([], intent.SCHEMA)
    complete([], intent.SCHEMA)
    assert formats == ["json_schema", "json_object", "json_object"]


@pytest.mark.parametrize("status,code", [
    (401, "bad_key"), (403, "bad_key"), (404, "bad_key"), (429, "limit_reached"),
    (500, "unparseable"), (503, "unparseable"),
])
def test_endpoint_failures_map_to_fixed_codes_and_never_echo_the_key(status, code):
    def handler(request):
        return httpx.Response(status, json={"error": {"message": "key sk-secret is wrong"}})

    complete = openai_complete("https://models.example/v1", "m", "sk-secret",
                               client=transport(handler), resolve=public)
    with pytest.raises(EngineError) as caught:
        complete([], None)
    assert caught.value.code == code
    assert caught.value.reason == f"the model provider answered {status}"
    assert "sk-secret" not in str(caught.value)


def test_a_timeout_is_reported_without_the_key():
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    complete = openai_complete("https://models.example/v1", "m", "sk-secret",
                               client=transport(handler), resolve=public)
    with pytest.raises(EngineError) as caught:
        complete([], None)
    assert caught.value.code == "unparseable"
    assert caught.value.status == 502


@pytest.mark.parametrize("url,address", [
    ("http://models.example/v1", "104.18.0.1"),
    ("https://models.example/v1", "127.0.0.1"),
    ("https://models.example/v1", "10.0.0.5"),
    ("https://models.example/v1", "169.254.169.254"),
    ("https://user:pw@models.example/v1", "104.18.0.1"),
])
def test_a_model_address_must_be_public_https(url, address):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=completion("ok"))

    def resolve(host, port, **kwargs):
        return [(2, 1, 6, "", (address, port))]

    complete = openai_complete(url, "m", "k", client=transport(handler), resolve=resolve)
    with pytest.raises(EngineError) as caught:
        complete([], None)
    assert caught.value.code == "bad_key"
    assert calls == []


def test_a_host_checked_once_is_not_looked_up_again_on_every_call():
    lookups = []

    def resolve(host, port, **kwargs):
        lookups.append(host)
        return [(2, 1, 6, "", ("104.18.0.1", port))]

    def handler(request):
        return httpx.Response(200, json=completion("ok"))

    for _ in range(3):
        openai_complete("https://models.example/v1", "m", "k", client=transport(handler),
                        resolve=resolve)([], None)
    assert lookups == ["models.example"]


def test_a_private_address_is_allowed_when_self_hosting_says_so():
    def handler(request):
        return httpx.Response(200, json=completion("ok"))

    def resolve(host, port, **kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", port))]

    complete = openai_complete("http://localhost:11434/v1", "m", "k", client=transport(handler),
                               resolve=resolve, allow_private=True)
    assert complete([], None) == "ok"


def test_actions_are_plain_typed_values():
    action = Action(op="create", entity="expense", amount=40000)
    assert action.repayment is False and action.target_latest is False


def test_an_endpoint_that_refused_a_schema_is_remembered_across_requests():
    formats = []

    def handler(request):
        formats.append(json.loads(request.content)["response_format"]["type"])
        if formats[-1] == "json_schema":
            return httpx.Response(400, json={"error": {"message": "response_format"}})
        return httpx.Response(200, json=completion('{"actions": []}'))

    for _ in range(2):
        openai_complete("https://plain-json.example/v1", "m", "k", client=transport(handler),
                        resolve=public)([], intent.SCHEMA)
    assert formats == ["json_schema", "json_object", "json_object"]


def test_a_currency_the_message_never_names_is_refused():
    with pytest.raises(EngineError) as caught:
        judge("had lunch with friends, 400", TODAY, CONTEXT, stub({"actions": [
            blank(op="create", entity="expense", amount="400", currency="GBP")]}))
    assert caught.value.code == "unparseable"


def test_a_currency_the_message_names_is_kept():
    [action] = judge("lunch in london came to 40 pounds", TODAY, CONTEXT, stub({"actions": [
        blank(op="create", entity="expense", amount="40", currency="gbp")]}))
    assert (action.amount, action.currency) == (4000, "GBP")


@pytest.mark.parametrize("content", [
    {"actions": []},
    {"actions": [blank(op="query", metric="spending")] * 6},
    {"actions": [blank(op="update", entity="expense", amount="400")]},
    {"actions": [blank(op="create", entity="expense", amount="0")]},
    {"actions": [blank(op="create", entity="expense", amount="400 or 500")]},
    {"actions": [blank(op="create", entity="spaceship", amount="400")]},
    {"actions": [blank(op="create", entity="expense", amount="400", date="soon")]},
    {"actions": [blank(op="query", metric=None)]},
    {"actions": [blank(op="clarify", question=None)]},
    {"actions": [blank(op="create", entity="expense", amount=400.5)]},
    {"actions": "all of them"},
    {"not_actions": []},
])
def test_a_malformed_model_answer_is_refused(content):
    with pytest.raises(EngineError) as caught:
        judge("spent 400 or 500 on dinner", TODAY, CONTEXT, stub(content))
    assert caught.value.code == "unparseable"


def test_a_response_with_no_content_is_refused():
    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    complete = openai_complete("https://models.example/v1", "m", "k", client=transport(handler),
                               resolve=public)
    with pytest.raises(EngineError) as caught:
        complete([], None)
    assert (caught.value.code, caught.value.status) == ("unparseable", 502)


def test_a_model_address_that_does_not_resolve_is_refused():
    def resolve(host, port, **kwargs):
        raise OSError("no such host")

    complete = openai_complete("https://nowhere.example/v1", "m", "k",
                               client=transport(lambda r: httpx.Response(200)), resolve=resolve)
    with pytest.raises(EngineError) as caught:
        complete([], None)
    assert caught.value.code == "bad_key"


def test_the_shared_client_keeps_no_cookies_between_callers():
    from engine import http

    def handler(request):
        assert "cookie" not in request.headers
        return httpx.Response(200, headers={"set-cookie": "session=someone; Path=/"},
                              json=completion("ok"))

    client = http.make_client(transport=httpx.MockTransport(handler))
    for _ in range(2):
        client.post("https://models.example/v1/chat/completions", json={})
    assert not client.cookies


# What Groq's strict mode said about openai/gpt-oss-120b's real answer to
# "i wanaa edit my expenses" on staging's data: the model writes null for a flag.
GROQ_SCHEMA_MISS = {"error": {
    "message": "Generated JSON does not match the expected schema. Please adjust your prompt. "
               "See 'failed_generation' for more details. Error: jsonschema: "
               "'/actions/0/target_latest' does not validate with "
               "/properties/actions/items/properties/target_latest/type: "
               "expected boolean, but got null",
    "type": "invalid_request_error", "code": "json_validate_failed"}}


def test_the_schema_takes_the_null_flags_the_default_model_writes():
    answer = {"actions": [blank(op="clarify", question="Which expense?",
                                repayment=None, target_latest=None)]}
    jsonschema.validate(answer, intent.SCHEMA)
    [action] = judge("i wanaa edit my expenses", TODAY, CONTEXT, stub(answer))
    assert (action.op, action.repayment, action.target_latest) == ("clarify", False, False)


def test_an_answer_that_misses_the_schema_does_not_switch_the_endpoint_to_plain_json():
    formats = []

    def handler(request):
        formats.append(json.loads(request.content)["response_format"]["type"])
        if len(formats) == 1:
            return httpx.Response(400, json=GROQ_SCHEMA_MISS)
        return httpx.Response(200, json=completion('{"actions": []}'))

    def complete():
        return openai_complete(intent.DEFAULT_BASE_URL, intent.DEFAULT_MODEL, "k",
                               client=transport(handler), resolve=public)

    with pytest.raises(EngineError) as caught:
        complete()([], intent.SCHEMA)
    assert (caught.value.code, caught.value.status) == ("unparseable", 502)
    assert caught.value.reason == "the model's answer did not match the schema"
    complete()([], intent.SCHEMA)
    assert formats == ["json_schema", "json_schema"]


def test_plain_json_mode_tells_the_model_the_shape_it_must_answer_in():
    sent = []

    def handler(request):
        body = json.loads(request.content)
        sent.append(body)
        if body["response_format"]["type"] == "json_schema":
            return httpx.Response(400, json={"error": {"message": "response_format"}})
        return httpx.Response(200, json=completion('{"actions": []}'))

    openai_complete("https://plain.example/v1", "m", "k", client=transport(handler),
                    resolve=public)([{"role": "user", "content": "hi"}], intent.SCHEMA)
    plain = sent[-1]
    assert plain["response_format"] == {"type": "json_object"}
    told = [m["content"] for m in plain["messages"] if m["role"] == "system"]
    assert told and json.dumps(intent.SCHEMA) in told[-1]


def test_the_model_sees_each_account_name_on_its_own():
    # Shown as "Cash (INR, default)", the default model copied that whole label
    # back as the account name, and the booking found no such account.
    calls = []
    judge("got a toothpaste for 60", TODAY, CONTEXT,
          stub({"actions": [blank(op="create", entity="expense", amount="60")]}, calls))
    sent = json.loads(calls[0][0][-1]["content"])
    assert sent["accounts"] == [{"name": "HDFC", "currency": "INR", "default": True},
                                {"name": "Cash", "currency": "INR", "default": False}]
