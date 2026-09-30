"""The terminal posts a message, not a state blob, sends the user's own model
key as headers, and renders every part of the chat contract."""

import asyncio
import importlib.util
import os
import types
from pathlib import Path

import requests
from rich.console import Console


def _errors():
    path = Path("whatsmynote/app/ui/errors.py")
    spec = importlib.util.spec_from_file_location("wmn_errors", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CODES = {
    "unauthenticated",
    "bad_key",
    "no_key",
    "rate_unavailable",
    "no_account",
    "unsupported_currency",
    "ambiguous",
    "unparseable",
    "limit_reached",
}


def _plain(renderable, width=80):
    console = Console(width=width, record=True, color_system=None, file=open(os.devnull, "w"))
    console.print(renderable)
    return console.export_text()


def test_every_code_renders_its_own_sentence():
    errors = _errors()
    assert set(errors.SENTENCES) == CODES
    rendered = {errors.sentence_for({"code": code}) for code in CODES}
    assert len(rendered) == len(CODES)


def test_an_unknown_code_never_shows_the_server_message():
    errors = _errors()
    body = {"code": "surprise", "message": "key sk-secret leaked"}
    assert errors.sentence_for(body) == errors.UNKNOWN


def test_chat_posts_the_message_and_not_a_state_blob():
    source = Path("whatsmynote/app/client.py").read_text()
    assert '{"message": message}' in source
    assert '"state"' not in source
    assert "X-Groq" not in source
    assert "app_state" not in source


def test_terminal_does_not_initialise_an_error_reporter():
    root = Path("whatsmynote")
    for path in root.rglob("*.py"):
        text = path.read_text()
        assert "sentry_sdk" not in text, path


# --- model key --------------------------------------------------------------


def test_no_model_headers_without_a_key():
    from whatsmynote.app.config import ModelSettings

    assert ModelSettings().headers() == {}
    assert ModelSettings(base_url="https://x.test/v1", name="m").headers() == {}


def test_model_headers_carry_key_base_url_and_name():
    from whatsmynote.app.config import ModelSettings

    settings = ModelSettings(key="sk-abcdefgh1234", base_url="https://x.test/v1", name="small")
    assert settings.headers() == {
        "X-Model-Key": "sk-abcdefgh1234",
        "X-Model-Base-URL": "https://x.test/v1",
        "X-Model-Name": "small",
    }
    assert settings.masked() == "...1234"
    assert "abcdefgh" not in settings.masked()


def test_key_store_saves_changes_and_clears(tmp_path):
    from whatsmynote.app.config import ModelKeyStore, ModelSettings

    path = tmp_path / "config.env"
    path.write_text("OTHER=1\nGROQ_API_KEY=old\n")
    store = ModelKeyStore(path)
    assert store.load().key == "old"

    store.save(ModelSettings(key="sk-new-key-9999", base_url="https://x.test/v1"))
    assert store.load() == ModelSettings(key="sk-new-key-9999", base_url="https://x.test/v1")
    assert "OTHER=1" in path.read_text()
    assert "GROQ_API_KEY" not in path.read_text()
    if os.name != "nt":
        assert path.stat().st_mode & 0o777 == 0o600

    store.save(ModelSettings(key="sk-new-key-9999"))
    assert store.load().base_url == ""

    store.clear()
    assert store.load() == ModelSettings()
    assert path.read_text() == "OTHER=1\n"


def test_key_settings_are_checked_before_saving():
    from whatsmynote.app.config import check_model_settings

    assert check_model_settings("", "", "")
    assert check_model_settings("sk key", "", "")
    assert check_model_settings("sk-1", "api.openai.com", "")
    assert check_model_settings("sk-1", "https://api.openai.com/v1", "gpt-4o-mini") is None


# --- the contract -------------------------------------------------------------


class Response:
    def __init__(self, status, body):
        self.status_code = status
        self.body = body

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body


class Http:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, json=None, headers=None, timeout=None):
        self.calls.append({"method": method, "url": url, "json": json, "headers": headers})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _client(http, key=""):
    from whatsmynote.app.client import EngineClient
    from whatsmynote.app.config import ModelSettings

    return EngineClient(
        "https://engine.test/", lambda: "session-token",
        lambda: ModelSettings(key=key, base_url="https://x.test/v1" if key else ""), http=http,
    )


def test_chat_sends_the_token_and_the_model_headers():
    http = Http(Response(200, {"reply": "Saved.", "balance": 60000, "confirmation": None,
                               "observations": []}))
    result = _client(http, key="sk-user-key-1234").chat("spent 400 on dinner")

    call = http.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://engine.test/chat"
    assert call["json"] == {"message": "spent 400 on dinner"}
    assert call["headers"]["Authorization"] == "Bearer session-token"
    assert call["headers"]["X-Model-Key"] == "sk-user-key-1234"
    assert call["headers"]["X-Model-Base-URL"] == "https://x.test/v1"
    assert result.reply == "Saved."
    assert result.balance == 60000


def test_chat_without_a_key_sends_no_model_headers():
    http = Http(Response(200, {"reply": "ok"}))
    _client(http).chat("hi")
    assert not any(name.startswith("X-Model") for name in http.calls[0]["headers"])


def test_confirm_posts_the_token():
    http = Http(Response(200, {"reply": "Deleted.", "balance": 100}))
    result = _client(http).confirm("tok-1")
    assert http.calls[0]["url"] == "https://engine.test/confirm"
    assert http.calls[0]["json"] == {"token": "tok-1"}
    assert result.reply == "Deleted."


def test_a_full_response_is_read():
    from whatsmynote.app.client import Confirmation, Observation, read_result

    result = read_result(200, {
        "reply": "Found it.",
        "balance": None,
        "confirmation": {"token": "t", "summary": "Delete dinner?"},
        "observations": [{"kind": "warning", "category": "food", "detail": "Third dinner out."}],
    })
    assert result.confirmation == Confirmation("t", "Delete dinner?")
    assert result.observations == (Observation("warning", "food", "Third dinner out."),)
    assert result.error == ""


def test_an_older_server_response_is_tolerated():
    from whatsmynote.app.client import read_result

    result = read_result(200, {"balance": 60000})
    assert result.reply == ""
    assert result.balance == 60000
    assert result.confirmation is None
    assert result.observations == ()


def test_every_error_code_becomes_its_sentence():
    from whatsmynote.app.client import read_result

    errors = _errors()
    for code in CODES:
        result = read_result(422, {"code": code, "message": "internal detail"})
        assert result.error == errors.SENTENCES[code]
        assert result.code == code
        assert "internal detail" not in result.error


def test_transport_failures_have_their_own_sentences():
    errors = _errors()
    assert _client(Http(requests.ConnectionError())).chat("x").error == errors.OFFLINE
    assert _client(Http(requests.Timeout())).chat("x").error == errors.TIMEOUT
    assert _client(Http(Response(502, ValueError("not json")))).chat("x").error == errors.SERVER
    assert _client(Http(Response(410, {"message": "gone"}))).confirm("t").error == errors.CONFIRM_FAILED


def test_balances_are_read_and_accounts_are_opened():
    http = Http(
        Response(200, {"balances": [{"name": "Cash", "currency": "INR", "current_balance": 150}]}),
        Response(200, {"status": "ok"}),
    )
    client = _client(http)
    assert client.balances().rows == [{"name": "Cash", "currency": "INR", "current_balance": 150}]
    assert client.open_account("Cash", "INR", 150050).error == ""
    assert http.calls[1]["json"] == {"name": "Cash", "currency": "INR", "opening_balance": 150050}


# --- rendering ----------------------------------------------------------------


def test_minor_units_are_shown_as_amounts():
    from whatsmynote.app.ui.present import format_minor

    assert format_minor(60000) == "600.00"
    assert format_minor(150050, "INR") == "1,500.50 INR"
    assert format_minor(-5) == "-0.05"


def test_typed_amounts_are_read_as_minor_units():
    from whatsmynote.app.ui.dialogs import parse_amount

    assert parse_amount("") == 0
    assert parse_amount("1500") == 150000
    assert parse_amount("1,500.5") == 150050
    assert parse_amount("-20.25") == -2025
    assert parse_amount("12,34") is None
    assert parse_amount("ten") is None


def test_a_reply_shows_its_text_observations_and_confirmation():
    from whatsmynote.app.client import read_result
    from whatsmynote.app.ui.present import result_renderables

    result = read_result(200, {
        "reply": "Found the dinner.",
        "balance": 60000,
        "confirmation": {"token": "t", "summary": "Delete dinner for 400.00?"},
        "observations": [{"kind": "warning", "category": "food", "detail": "Third dinner out."}],
    })
    text = "".join(_plain(part) for part in result_renderables(result))
    assert "Found the dinner." in text
    assert "food" in text and "Third dinner out." in text
    assert "Delete dinner for 400.00?" in text
    assert "y confirm" in text and "n cancel" in text
    assert "600.00" not in text


def test_no_reply_shows_the_balance():
    from whatsmynote.app.client import read_result
    from whatsmynote.app.ui.present import result_renderables

    text = "".join(_plain(part) for part in result_renderables(read_result(200, {"balance": 60000})))
    assert "Balance" in text and "600.00" in text
    assert "60000" not in text


def test_server_text_is_not_read_as_markup():
    from whatsmynote.app.client import read_result
    from whatsmynote.app.ui.present import result_renderables

    text = _plain(result_renderables(read_result(200, {"reply": "[bold]x[/] [/oops]"}))[0])
    assert "[bold]x[/] [/oops]" in text


def test_the_welcome_fits_eighty_columns_and_says_what_to_type():
    from whatsmynote.app.ui.present import welcome

    text = _plain(welcome(signed_in=False), width=76)
    assert "/login" in text and "Google" in text and "GitHub" in text
    assert "/key" in text
    assert "spent 400 on dinner" in text
    assert all(len(line) <= 76 for line in text.splitlines())


# --- the app, at 80 by 24 -----------------------------------------------------


class FakeAuth:
    def __init__(self, user=None):
        self.user = user
        self.passwords = []

    def restore(self):
        return self.user

    def access_token(self):
        return "token" if self.user else None

    def sign_in(self, email, password):
        self.passwords.append(password)
        return types.SimpleNamespace(email=email, user_metadata={})

    def sign_out(self):
        self.user = None


class FakeEngine:
    def __init__(self, replies=()):
        self.replies = list(replies)
        self.sent = []
        self.confirmed = []

    def chat(self, message):
        from whatsmynote.app.client import read_result

        self.sent.append(message)
        return read_result(200, self.replies.pop(0))

    def confirm(self, token):
        from whatsmynote.app.client import read_result

        self.confirmed.append(token)
        return read_result(200, {"reply": "Deleted.", "balance": 100})

    def balances(self):
        from whatsmynote.app.client import Balances

        return Balances(rows=[{"name": "Cash", "currency": "INR", "current_balance": 150050}])


ADA = types.SimpleNamespace(email="ada@example.com", user_metadata={"full_name": "Ada Lovelace"})


def _run(test, tmp_path, user=None, replies=()):
    from whatsmynote.app.config import ModelKeyStore
    from whatsmynote.app.ui.app import WhatsMyNoteApp

    auth, engine = FakeAuth(user), FakeEngine(replies)
    app = WhatsMyNoteApp(auth=auth, engine=engine, keys=ModelKeyStore(tmp_path / "config.env"))

    async def go():
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await test(app, pilot)

    asyncio.run(go())
    return app, auth, engine


async def _type(pilot, line):
    await pilot.press(*line)
    await pilot.press("enter")
    await pilot.pause(0.1)


def _screen_text(app):
    return "".join(_plain(message.source) for message in app.screen.query(".message"))


def test_signed_out_first_screen_points_to_login(tmp_path):
    async def check(app, pilot):
        assert "/login" in _screen_text(app)
        assert "not signed in" in str(app.screen.query_one("#who").render())
        await _type(pilot, "spent 400 on dinner")
        assert "Sign in first" in _screen_text(app)

    _, _, engine = _run(check, tmp_path)
    assert engine.sent == []


def test_a_confirmation_is_asked_and_confirmed(tmp_path):
    replies = [{"reply": "Found it.", "confirmation": {"token": "tok-9", "summary": "Delete dinner?"}}]

    async def check(app, pilot):
        await _type(pilot, "delete dinner")
        assert "Delete dinner?" in _screen_text(app)
        assert app.screen.pending is not None
        await _type(pilot, "maybe")
        assert app.screen.pending is not None
        await _type(pilot, "y")
        await pilot.pause(0.1)
        assert app.screen.pending is None
        assert "Deleted." in _screen_text(app)

    _, _, engine = _run(check, tmp_path, user=ADA, replies=replies)
    assert engine.sent == ["delete dinner"]
    assert engine.confirmed == ["tok-9"]


def test_a_confirmation_can_be_declined(tmp_path):
    replies = [{"confirmation": {"token": "tok-9", "summary": "Delete dinner?"}}]

    async def check(app, pilot):
        await _type(pilot, "delete dinner")
        await _type(pilot, "n")
        assert app.screen.pending is None
        assert "Nothing was saved" in _screen_text(app)

    _, _, engine = _run(check, tmp_path, user=ADA, replies=replies)
    assert engine.confirmed == []


def test_the_key_dialog_saves_and_removes_the_key(tmp_path):
    async def check(app, pilot):
        await _type(pilot, "/key")
        await pilot.pause(0.1)
        await pilot.press(*"sk-test-key-5678")
        await pilot.press("enter", "enter", "enter")
        await pilot.pause(0.1)
        assert app.keys.load().key == "sk-test-key-5678"
        assert "sk-test-key-5678" not in _screen_text(app)
        assert "...5678" in _screen_text(app)

        await _type(pilot, "/key")
        await pilot.pause(0.1)
        await pilot.click(".remove")
        await pilot.pause(0.1)
        assert app.keys.load().key == ""

    _run(check, tmp_path, user=ADA)


def test_email_sign_in_keeps_the_password_away_from_the_engine(tmp_path):
    async def check(app, pilot):
        await _type(pilot, "/login")
        await pilot.press("1")
        await pilot.pause(0.1)
        await pilot.press(*"ada@example.com")
        await pilot.press("enter")
        await pilot.press(*"hunter22")
        await pilot.press("enter")
        await pilot.pause(0.3)
        assert app.screen.user is not None
        assert "Signed in as ada@example.com" in _screen_text(app)
        assert "hunter22" not in _screen_text(app)

    _, auth, engine = _run(check, tmp_path)
    assert auth.passwords == ["hunter22"]
    assert engine.sent == []


def test_an_unknown_command_suggests_the_nearest(tmp_path):
    async def check(app, pilot):
        await _type(pilot, "/kye")
        assert "Did you mean /key?" in _screen_text(app)

    _run(check, tmp_path, user=ADA)


def test_balances_finishing_first_does_not_release_a_running_message(tmp_path):
    import threading

    release = threading.Event()

    class SlowEngine(FakeEngine):
        def chat(self, message):
            release.wait(5)
            return super().chat(message)

    async def check(app, pilot):
        app.engine = SlowEngine([{"reply": "one"}, {"reply": "two"}])
        await _type(pilot, "first")
        await _type(pilot, "/balances")
        await pilot.pause(0.2)
        await _type(pilot, "second")
        assert "Still working on your last message" in _screen_text(app)
        release.set()
        await pilot.pause(0.3)
        assert app.engine.sent == ["first"]

    _run(check, tmp_path, user=ADA)


def test_sign_in_waits_for_the_saved_session_check(tmp_path):
    import threading

    release = threading.Event()

    class SlowAuth(FakeAuth):
        def restore(self):
            release.wait(5)
            return None

    async def check(app, pilot):
        await _type(pilot, "/login")
        assert "Still checking for a saved sign-in" in _screen_text(app)
        assert not app.screen_stack[-1].query("#sign-in-choices")
        release.set()
        await pilot.pause(0.2)
        assert "not signed in" in str(app.screen.query_one("#who").render())

    from whatsmynote.app.config import ModelKeyStore
    from whatsmynote.app.ui.app import WhatsMyNoteApp

    app = WhatsMyNoteApp(auth=SlowAuth(), engine=FakeEngine(), keys=ModelKeyStore(tmp_path / "c.env"))

    async def go():
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await check(app, pilot)

    asyncio.run(go())
