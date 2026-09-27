"""The terminal posts a message, not a state blob, and renders error codes."""

import importlib.util
from pathlib import Path


def _errors():
    path = Path("whatsmynote/app/ui/errors.py")
    spec = importlib.util.spec_from_file_location("wmn_errors", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CODES = {
    "unauthenticated",
    "bad_key",
    "rate_unavailable",
    "no_account",
    "unsupported_currency",
    "ambiguous",
    "unparseable",
}


def test_every_code_renders_its_own_sentence():
    errors = _errors()
    assert set(errors.SENTENCES) == CODES
    rendered = {errors.sentence_for({"code": code}) for code in CODES}
    assert len(rendered) == len(CODES)


def test_chat_posts_the_message_and_not_a_state_blob():
    from pathlib import Path

    source = Path("whatsmynote/app/ui/mixins/chat.py").read_text()
    assert '"message": message' in source
    assert '"state"' not in source
    assert "X-Groq" not in source
    assert "app_state" not in source


def test_terminal_does_not_initialise_an_error_reporter():
    from pathlib import Path

    root = Path("whatsmynote")
    for path in root.rglob("*.py"):
        text = path.read_text()
        assert "sentry_sdk" not in text, path
