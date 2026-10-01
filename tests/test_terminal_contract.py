"""The terminal's client against the real engine app, over its HTTP surface.

Each test runs the client the terminal uses through the engine built from
engine.api, with a scripted model, so a change on either side of the chat
contract fails here."""

import pytest
from fastapi.testclient import TestClient

from tests.support import ALICE
from tests.test_api import Model, Verifier, act, actions

KEY = "sk-terminal-contract-0123456789"


class Http:
    """Lets the client's requests.request(...) calls reach a TestClient."""

    def __init__(self, client):
        self.client = client

    def request(self, method, url, json=None, headers=None, timeout=None):
        return self.client.request(method, url, json=json, headers=headers)


@pytest.fixture
def terminal(dsn):
    from datetime import date

    from engine.api import build_app
    from whatsmynote.app.client import EngineClient
    from whatsmynote.app.config import ModelSettings

    model = Model()
    settings = {"value": ModelSettings()}
    app = build_app(dsn=dsn, verify=Verifier({"alice-token": ALICE}),
                    complete_for=model.complete_for, fetch_rate=None,
                    today=lambda: date(2026, 9, 26), daily_limit=5)
    with TestClient(app) as client:
        engine = EngineClient("http://testserver", lambda: "alice-token",
                              lambda: settings["value"], http=Http(client))
        yield engine, model, settings


def test_a_clear_booking_works_without_a_key(terminal):
    engine, model, _ = terminal
    assert engine.open_account("HDFC", "INR", 100000).error == ""
    result = engine.chat("spent 400 on dinner")
    assert result.error == ""
    assert result.reply
    assert result.balance == 60000
    assert model.calls == []
    assert engine.balances().rows[0]["name"] == "HDFC"


def test_a_message_that_needs_the_model_asks_for_a_key(terminal):
    from whatsmynote.app.ui.errors import SENTENCES

    engine, _, _ = terminal
    engine.open_account("HDFC", "INR", 100000)
    result = engine.chat("dinner with friends came to 1200, split three ways")
    assert (result.code, result.error) == ("no_key", SENTENCES["no_key"])


def test_the_key_goes_with_the_message_and_a_delete_is_confirmed_once(terminal):
    from whatsmynote.app.config import ModelSettings
    from whatsmynote.app.ui.errors import CONFIRM_FAILED

    engine, model, settings = terminal
    engine.open_account("HDFC", "INR", 100000)
    engine.chat("paid 250 for uber")
    settings["value"] = ModelSettings(key=KEY, name="small-model")
    model.say(actions(act(op="delete", entity="expense", target_text="uber")))

    asked = engine.chat("delete the uber")
    assert model.calls[0]["config"].key == KEY
    assert model.calls[0]["config"].name == "small-model"
    assert asked.confirmation and "uber" in asked.confirmation.summary

    done = engine.confirm(asked.confirmation.token)
    assert done.error == ""
    assert done.balance == 100000
    assert done.reply.startswith("Deleted")

    again = engine.confirm(asked.confirmation.token)
    assert again.error == CONFIRM_FAILED
