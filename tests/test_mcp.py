"""The MCP server is a stdio client of the engine's HTTP API.

Identity is the access token in the server's environment. No tool takes a user
id or a token, so a tool call can only ever act for the token's own user.
"""

import asyncio
import json
import subprocess
import sys
import tomllib
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from mcp import Client, StdioServerParameters

from tests.support import ALICE, BOB
from whatsmynote.mcp_server import Api, build_server

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {"ask", "confirm", "balances", "spending", "records", "open_account", "set_budget"}


class Model:
    def __init__(self):
        self.configs = []

    def complete_for(self, config):
        self.configs.append(config)

        def complete(messages, schema=None):
            return json.dumps({"actions": [{
                "op": "query", "entity": None, "amount": None, "currency": None,
                "category": None, "note": None, "account": None, "to_account": None,
                "person": None, "direction": None, "repayment": False, "date": None,
                "due": None, "period": None, "target_text": None, "target_amount": None,
                "target_date": None, "target_latest": False, "metric": "balances",
                "range": None, "start": None, "end": None, "order": None, "question": None}]})
        return complete


@pytest.fixture
def engine(dsn):
    from engine.api import build_app

    model = Model()
    app = build_app(dsn=dsn, verify={"alice-token": ALICE, "bob-token": BOB}.get,
                    complete_for=model.complete_for, fetch_rate=None,
                    today=lambda: date(2026, 9, 26))
    with TestClient(app) as client:
        yield client, model


def call(server, name, arguments=None):
    async def go():
        async with Client(server) as client:
            result = await client.call_tool(name, arguments or {})
            return result.structured_content, result.is_error
    return asyncio.run(go())


def server_for(engine, token, **model):
    client, _ = engine
    return build_server(Api("http://testserver", token, client=client, **model))


def test_no_tool_takes_a_user_id_or_a_token(engine):
    async def go():
        async with Client(server_for(engine, "alice-token")) as client:
            return (await client.list_tools()).tools
    tools = asyncio.run(go())
    assert {tool.name for tool in tools} == TOOLS
    for tool in tools:
        properties = set(tool.input_schema.get("properties", {}))
        assert not properties & {"user_id", "user", "token", "access_token"}, tool.name


def test_a_tool_acts_only_for_the_token_in_its_environment(engine):
    bob = server_for(engine, "bob-token")
    alice = server_for(engine, "alice-token")
    opened, error = call(bob, "open_account", {"name": "HDFC", "currency": "INR",
                                               "opening_balance": 1000})
    assert not error and opened["status"] == "ok"
    booked, _ = call(bob, "ask", {"message": "spent 400 on dinner"})
    assert booked["balance"] == 60000

    mine, _ = call(alice, "balances")
    assert mine == {"balances": []}
    named, error = call(alice, "balances", {"user_id": BOB})
    assert error or named == {"balances": []}
    spent, _ = call(alice, "spending", {"start": "2026-09-01", "end": "2026-09-30"})
    assert spent == {"spending": []}
    assert call(bob, "records")[0]["records"][0]["raw_text"] == "spent 400 on dinner"


def test_budgets_and_accounts_take_major_units(engine):
    alice = server_for(engine, "alice-token")
    call(alice, "open_account", {"name": "Cash", "currency": "INR", "opening_balance": 250.5})
    budget, _ = call(alice, "set_budget", {"category": "food", "amount": 3000})
    assert budget["budget"]["amount"] == 300000
    assert call(alice, "balances")[0]["balances"][0]["current_balance"] == 25050


def test_the_model_settings_travel_as_request_headers(engine):
    _, model = engine
    alice = server_for(engine, "alice-token", model_key="sk-mcp", model_name="some-model",
                       model_base_url="https://models.example/v1")
    answer, _ = call(alice, "ask", {"message": "tell me my balances please"})
    assert "no accounts" in answer["reply"]
    config = model.configs[-1]
    assert (config.key, config.name, config.base_url) == (
        "sk-mcp", "some-model", "https://models.example/v1")


def test_a_rejected_token_comes_back_as_the_error_code(engine):
    answer, _ = call(server_for(engine, "expired-token"), "balances")
    assert answer["code"] == "unauthenticated"
    assert "WMN_ACCESS_TOKEN" in answer["message"]


def test_the_console_script_is_declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["scripts"]["whatsmynote-mcp"] == "whatsmynote.mcp_server:main"


def test_the_stdio_server_starts_and_lists_its_tools():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "whatsmynote.mcp_server"], cwd=str(ROOT),
        env={"WMN_ACCESS_TOKEN": "token", "WMN_API_URL": "http://127.0.0.1:9"})

    async def go():
        async with Client(params, read_timeout_seconds=30) as client:
            return {tool.name for tool in (await client.list_tools()).tools}
    assert asyncio.run(go()) == TOOLS


def test_the_stdio_server_will_not_start_without_a_token():
    result = subprocess.run([sys.executable, "-m", "whatsmynote.mcp_server"], cwd=ROOT,
                            env={"PATH": "/usr/bin:/bin"}, capture_output=True, text=True,
                            timeout=30, stdin=subprocess.DEVNULL)
    assert result.returncode != 0
    assert "WMN_ACCESS_TOKEN" in result.stderr


def test_confirm_passes_the_confirmation_to_the_api(engine):
    answer, _ = call(server_for(engine, "alice-token"), "confirm", {"confirmation": "stale"})
    assert answer["code"] == "ambiguous"
    assert "expired" in answer["message"]


def test_an_unreachable_api_is_reported_plainly():
    import httpx

    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    api = Api("http://api.example", "t", client=httpx.Client(transport=httpx.MockTransport(refuse)))
    assert api.get("/balances") == {"code": "internal",
                                    "message": "The WhatsMyNote API could not be reached."}


def test_a_server_error_page_becomes_a_code():
    import httpx

    api = Api("http://api.example", "t", client=httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(502, text="<html>bad gateway</html>"))))
    assert api.get("/balances") == {"code": "internal", "message": "The API answered 502."}


def test_amounts_that_are_not_numbers_are_refused(engine):
    alice = server_for(engine, "alice-token")
    for amount in ("nan", "inf"):
        answer, _ = call(alice, "set_budget", {"category": "food", "amount": amount})
        assert answer["code"] == "unparseable"
