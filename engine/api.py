"""The HTTP surface. Identity comes from the verified token and is applied as
the transaction role; nothing in a request body can name a user.

The caller's model key arrives in a header, is used for that request only, and
is never stored, logged, or echoed: an unexpected failure is logged with the key
scrubbed out, and every error body is written here from a fixed code.
"""

import hashlib
import logging
import os
import threading
import time
import traceback
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from engine import intent, queries
from engine.chat import Chat, Model
from engine.db import Database
from engine.errors import EngineError, sentence
from engine.ledger import is_minor, open_account, set_budget
from engine.queries import balances as query_balances
from engine.queries import spending_by_category
from engine.rates import frankfurter

_TOKEN_TTL = 60
_DEFAULT_DAILY_CALLS = 100
log = logging.getLogger("whatsmynote")


def build_app(dsn, verify, complete_for=None, fetch_rate=frankfurter, today=None,
              daily_limit=None, pool_size=5, allow_private_models=False, clock=time.monotonic):
    db = Database(dsn, size=pool_size)
    if complete_for is None:
        def complete_for(model):
            return intent.openai_complete(model.base_url, model.name, model.key,
                                          allow_private=allow_private_models)
    if daily_limit is None:
        daily_limit = int(os.environ.get("WMN_DAILY_MODEL_CALLS", _DEFAULT_DAILY_CALLS))
    if today is None:
        zone = ZoneInfo(os.environ.get("WMN_TIMEZONE", "UTC"))

        def today():
            return datetime.now(zone).date()

    chat = Chat(db, complete_for, fetch_rate, today, daily_limit)
    tokens = _TokenCache(verify, clock)

    @asynccontextmanager
    async def lifespan(app):
        yield
        db.close()

    app = FastAPI(lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    def malformed(request, error):
        if not tokens.user(request):
            return _refused(request, _SIGN_IN)
        return _refused(request, EngineError("unparseable", "the request body could not be read",
                                             reason="the body is not a JSON object"))

    def guarded(request, work):
        """Run an endpoint as the signed-in user, turning every failure into the
        fixed error body. Nothing about the model key reaches a log."""
        user = tokens.user(request)
        if not user:
            return _refused(request, _SIGN_IN)
        try:
            return work(user)
        except EngineError as error:
            return _refused(request, error)
        except Exception as error:
            key = request.headers.get("x-model-key")
            text = "".join(traceback.format_exception(error))
            log.error("%s %s 500 internal: %s", request.method, request.url.path,
                      text.replace(key, "[model key]") if key else text)
            return JSONResponse({"code": "internal", "message": sentence("internal")}, 500)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def site():
        page = Path(__file__).resolve().parents[1] / "web" / "index.html"
        return FileResponse(page)

    @app.post("/chat")
    def chat_turn(body: dict, request: Request):
        model = Model(
            key=request.headers.get("x-model-key") or None,
            base_url=request.headers.get("x-model-base-url") or intent.DEFAULT_BASE_URL,
            name=request.headers.get("x-model-name") or intent.DEFAULT_MODEL,
        )
        return guarded(request, lambda user: chat.reply(user, body.get("message"), model))

    @app.post("/confirm")
    def confirm_turn(body: dict, request: Request):
        return guarded(request, lambda user: chat.confirm(user, body.get("token")))

    @app.post("/accounts")
    def accounts(body: dict, request: Request):
        def work(user):
            name, currency, opening = (body.get("name"), body.get("currency"),
                                       body.get("opening_balance"))
            if not isinstance(name, str) or not isinstance(currency, str) \
                    or not is_minor(opening):
                raise EngineError("unparseable", "an account needs a name, a currency, "
                                                 "and an opening balance in minor units")
            with db.user(user) as conn:
                open_account(conn, name, currency, opening,
                             is_default=body.get("is_default") is True)
            return {"status": "ok"}
        return guarded(request, work)

    @app.post("/budgets")
    def budgets(body: dict, request: Request):
        def work(user):
            category, amount = body.get("category"), body.get("amount")
            period, currency = body.get("period") or "monthly", body.get("currency")
            if not isinstance(category, str) or not is_minor(amount) \
                    or not isinstance(period, str) or not isinstance(currency, (str, type(None))):
                raise EngineError("unparseable", "a budget needs a category, an amount in "
                                                 "minor units, and optionally a period and "
                                                 "a currency")
            with db.user(user) as conn:
                record_id = set_budget(conn, category, amount, period, currency)
                return {"status": "ok", "budget": queries.budget(conn, record_id)}
        return guarded(request, work)

    @app.get("/balances")
    def balances(request: Request):
        def work(user):
            with db.user(user) as conn:
                return {"balances": query_balances(conn)}
        return guarded(request, work)

    @app.get("/spending")
    def spending(request: Request, start: str, end: str):
        def work(user):
            with db.user(user) as conn:
                rows = spending_by_category(conn, _date(start), _date(end))
            return {"spending": [{"category": category, "converted_minor": amount}
                                 for category, amount in rows]}
        return guarded(request, work)

    @app.get("/records")
    def records(request: Request, type: str = "", start: str = "", end: str = "", q: str = ""):
        def work(user):
            with db.user(user) as conn:
                return {"records": queries.records(conn, type, start, end, q)}
        return guarded(request, work)

    return app


class _TokenCache:
    """Verified tokens, remembered for a minute by a hash so the token itself is
    never kept. Expired entries are dropped so the cache cannot grow without bound."""

    def __init__(self, verify, clock):
        self.verify = verify
        self.clock = clock
        self.entries = {}
        self.lock = threading.Lock()

    def user(self, request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1].strip()
        if not token:
            return None
        key = hashlib.sha256(token.encode()).hexdigest()
        now = self.clock()
        with self.lock:
            cached = self.entries.get(key)
            if cached and now - cached[1] < _TOKEN_TTL:
                return cached[0]
        user = self.verify(token)
        with self.lock:
            if len(self.entries) > 1000:
                self.entries = {k: v for k, v in self.entries.items() if now - v[1] < _TOKEN_TTL}
            if user:
                self.entries[key] = (user, now)
        return user


def _date(text):
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise EngineError("unparseable", "dates are written YYYY-MM-DD") from None


_SIGN_IN = EngineError("unauthenticated", "sign in first", reason="no valid sign-in token")


def _refused(request, error):
    """The fixed error body, after one log line naming the code, the check that
    refused, and where it was raised, so a refusal is never invisible. The line
    holds only fixed text: never the message, a name, or the key."""
    reason = f" ({error.reason})" if error.reason else ""
    log.warning("%s %s %s %s%s%s", request.method, request.url.path, error.status, error.code,
                reason, _raised_at(error))
    return JSONResponse({"code": error.code, "message": str(error)}, error.status)


def _raised_at(error):
    frames = traceback.extract_tb(error.__traceback__)
    if not frames:
        return ""
    last = frames[-1]
    return f" at {Path(last.filename).name}:{last.lineno} {last.name}"


_supabase = None
_supabase_lock = threading.Lock()


def _live_verify(token):
    """The user id a Supabase access token belongs to, or None when it is invalid
    or expired. The client is created once, so a check reuses its connection."""
    global _supabase
    from supabase import create_client
    from supabase_auth.errors import AuthApiError

    with _supabase_lock:
        if _supabase is None:
            _supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    try:
        result = _supabase.auth.get_user(token)
    except AuthApiError:
        return None
    if not result or not result.user:
        return None
    return result.user.id


def create_live_app():
    """The process Render starts. Tests build their own app and never call this."""
    database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    return build_app(database_url, _live_verify,
                     allow_private_models=os.environ.get("WMN_ALLOW_PRIVATE_MODEL_HOSTS") == "1")
