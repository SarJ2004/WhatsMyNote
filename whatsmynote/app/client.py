"""Talks to the engine over the shared chat contract.

The terminal sends the message, the session token, and the user's own model
settings as headers. It never sends a password or a state blob, and it reads
error bodies only for their code.
"""

from dataclasses import dataclass, field
from typing import Callable

import requests

from whatsmynote.app.config import ModelSettings
from whatsmynote.app.ui.errors import (
    CONFIRM_FAILED, OFFLINE, SENTENCES, SERVER, TIMEOUT, UNKNOWN, sentence_for,
)


@dataclass(frozen=True)
class Confirmation:
    token: str
    summary: str


@dataclass(frozen=True)
class Observation:
    kind: str
    category: str
    detail: str


@dataclass(frozen=True)
class Result:
    reply: str = ""
    balance: int | None = None
    confirmation: Confirmation | None = None
    observations: tuple[Observation, ...] = ()
    error: str = ""
    code: str = ""


@dataclass(frozen=True)
class Balances:
    rows: list = field(default_factory=list)
    error: str = ""
    code: str = ""


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _balance(value):
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _confirmation(value):
    if not isinstance(value, dict):
        return None
    token, summary = _text(value.get("token")), _text(value.get("summary"))
    if not token:
        return None
    return Confirmation(token=token, summary=summary or "Save this change?")


def _observations(value):
    if not isinstance(value, list):
        return ()
    found = []
    for item in value:
        if not isinstance(item, dict):
            continue
        detail = _text(item.get("detail"))
        if detail:
            found.append(Observation(_text(item.get("kind")), _text(item.get("category")), detail))
    return tuple(found)


def _failure(status, body, confirming=False):
    if confirming and status == 410:
        # A used or expired token. Whatever code it carries, say what happened.
        return CONFIRM_FAILED, ""
    if status >= 500:
        fallback = SERVER
    elif confirming:
        fallback = CONFIRM_FAILED
    else:
        fallback = UNKNOWN
    code = body.get("code") if isinstance(body, dict) else ""
    return sentence_for(body, fallback), code if code in SENTENCES else ""


def read_result(status: int, body, confirming: bool = False) -> Result:
    """Turn one /chat or /confirm response into a Result. Missing fields are fine."""
    if status >= 400 or (isinstance(body, dict) and body.get("code")):
        error, code = _failure(status, body, confirming)
        return Result(error=error, code=code)
    if not isinstance(body, dict):
        return Result(error=UNKNOWN)
    return Result(
        reply=_text(body.get("reply")),
        balance=_balance(body.get("balance")),
        confirmation=_confirmation(body.get("confirmation")),
        observations=_observations(body.get("observations")),
    )


class EngineClient:
    def __init__(
        self,
        base_url: str,
        token: Callable[[], str | None],
        model_settings: Callable[[], ModelSettings],
        http=requests,
        timeout: float = 90,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.model_settings = model_settings
        self.http = http
        self.timeout = timeout

    def _send(self, method, path, payload=None, with_model=False):
        """Return (status, body) or (None, sentence) when nothing came back."""
        token = self.token()
        if not token:
            return 401, {"code": "unauthenticated"}
        headers = {"Authorization": f"Bearer {token}"}
        if with_model:
            headers.update(self.model_settings().headers())
        try:
            response = self.http.request(
                method, f"{self.base_url}{path}", json=payload,
                headers=headers, timeout=self.timeout,
            )
        except requests.Timeout:
            return None, TIMEOUT
        except requests.RequestException:
            return None, OFFLINE
        try:
            body = response.json()
        except ValueError:
            body = None
        return response.status_code, body

    def chat(self, message: str) -> Result:
        status, body = self._send("POST", "/chat", {"message": message}, with_model=True)
        if status is None:
            return Result(error=body)
        return read_result(status, body)

    def confirm(self, token: str) -> Result:
        status, body = self._send("POST", "/confirm", {"token": token}, with_model=True)
        if status is None:
            return Result(error=body)
        return read_result(status, body, confirming=True)

    def balances(self) -> Balances:
        status, body = self._send("GET", "/balances")
        if status is None:
            return Balances(error=body)
        if status >= 400 or not isinstance(body, dict):
            error, code = _failure(status, body)
            return Balances(error=error, code=code)
        rows = body.get("balances")
        return Balances(rows=[row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else [])

    def open_account(self, name: str, currency: str, opening_balance: int) -> Result:
        payload = {"name": name, "currency": currency, "opening_balance": opening_balance}
        status, body = self._send("POST", "/accounts", payload)
        if status is None:
            return Result(error=body)
        if status >= 400:
            error, code = _failure(status, body)
            return Result(error=error, code=code)
        return Result()
