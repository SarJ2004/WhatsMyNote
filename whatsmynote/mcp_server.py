"""WhatsMyNote as MCP tools over stdio, for other agents.

The server is a thin client of the WhatsMyNote HTTP API. It acts for exactly one
person: the one whose Supabase access token is in WMN_ACCESS_TOKEN. No tool takes
a user id or a token, so a tool call can never act for anyone else. An optional
model key travels to the API as a request header on each chat call and is never
written anywhere.

Environment:
    WMN_ACCESS_TOKEN    required; a Supabase access token (they expire after an hour)
    WMN_API_URL         the API to call, default the staging service
    WMN_MODEL_KEY       optional; your OpenAI-compatible model key
    WMN_MODEL_BASE_URL  optional; the endpoint, default Groq
    WMN_MODEL_NAME      optional; the model, default the engine's choice

Run it with `whatsmynote-mcp`, or `python -m whatsmynote.mcp_server`.
"""

import os
import sys
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer

DEFAULT_API_URL = "https://whatsmynote-staging.onrender.com"
Result = dict[str, Any]
_EXPIRED = ("The API did not accept the access token. Sign in again and set "
            "WMN_ACCESS_TOKEN to a fresh Supabase access token.")


class Api:
    """The HTTP API, called with this person's token and model settings."""

    def __init__(self, base_url, token, client=None, model_key=None, model_base_url=None,
                 model_name=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = client or httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
        self.model = {"x-model-key": model_key, "x-model-base-url": model_base_url,
                      "x-model-name": model_name}

    def get(self, path, params=None):
        return self._send("GET", path, params=params)

    def post(self, path, body, with_model=False):
        return self._send("POST", path, json=body, with_model=with_model)

    def _send(self, method, path, with_model=False, **kwargs):
        headers = {"authorization": f"Bearer {self.token}"}
        if with_model:
            headers.update({k: v for k, v in self.model.items() if v})
        try:
            response = self.client.request(method, self.base_url + path, headers=headers,
                                           **kwargs)
        except httpx.HTTPError:
            return {"code": "internal", "message": "The WhatsMyNote API could not be reached."}
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code == 401:
            return {"code": "unauthenticated", "message": _EXPIRED}
        if response.status_code >= 400 and "code" not in body:
            return {"code": "internal", "message": f"The API answered {response.status_code}."}
        return body


def build_server(api):
    server = MCPServer("whatsmynote")

    @server.tool()
    def ask(message: str) -> Result:
        """Tell WhatsMyNote anything about your money, in plain words: book an expense,
        income, transfer, or loan ("spent 400 on dinner from HDFC"), change or delete an
        entry, or ask a question ("how much did I spend on food this month", "who owes
        me money"). Returns reply, balance (minor units of the account it touched),
        confirmation (a token to pass to confirm before a delete or an unclear change),
        and observations."""
        return api.post("/chat", {"message": message}, with_model=True)

    @server.tool()
    def confirm(confirmation: str) -> Result:
        """Carry out a change that ask asked to confirm. Pass the confirmation token ask
        returned; it is single-use and expires after ten minutes."""
        return api.post("/confirm", {"token": confirmation})

    @server.tool()
    def balances() -> Result:
        """Every account and its current balance, in minor units (hundredths)."""
        return api.get("/balances")

    @server.tool()
    def spending(start: str, end: str) -> Result:
        """Spending by category between two dates (YYYY-MM-DD), in minor units."""
        return api.get("/spending", {"start": start, "end": end})

    @server.tool()
    def records(type: str = "", start: str = "", end: str = "", query: str = "") -> Result:
        """Entries, most recent first, optionally filtered by type (expense, income,
        transfer, lending, account, budget), date range, and words."""
        return api.get("/records", {"type": type, "start": start, "end": end, "q": query})

    @server.tool()
    def open_account(name: str, currency: str, opening_balance: float) -> Result:
        """Open an account. opening_balance is in major units, such as 2500.50."""
        minor = _minor(opening_balance)
        if minor is None:
            return {"code": "unparseable", "message": "The opening balance is not a number."}
        return api.post("/accounts", {"name": name, "currency": currency,
                                      "opening_balance": minor})

    @server.tool()
    def set_budget(category: str, amount: float, period: str = "monthly") -> Result:
        """Set a monthly or weekly budget for a category. amount is in major units."""
        minor = _minor(amount)
        if minor is None:
            return {"code": "unparseable", "message": "The amount is not a number."}
        return api.post("/budgets", {"category": category, "amount": minor, "period": period})

    return server


def _minor(value):
    try:
        return int((Decimal(str(value)) * 100).to_integral_value())
    except (InvalidOperation, ValueError, OverflowError):
        return None


def main():
    token = os.environ.get("WMN_ACCESS_TOKEN", "").strip()
    if not token:
        print("whatsmynote-mcp: set WMN_ACCESS_TOKEN to your Supabase access token.",
              file=sys.stderr)
        sys.exit(2)
    api = Api(
        os.environ.get("WMN_API_URL") or DEFAULT_API_URL,
        token,
        model_key=os.environ.get("WMN_MODEL_KEY") or None,
        model_base_url=os.environ.get("WMN_MODEL_BASE_URL") or None,
        model_name=os.environ.get("WMN_MODEL_NAME") or None,
    )
    build_server(api).run("stdio")


if __name__ == "__main__":
    main()
