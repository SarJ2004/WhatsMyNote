"""The HTTP surface. Identity comes from the verified token and is applied as
the transaction role; nothing in a request body can name a user.
"""

import hashlib
import time

import psycopg2
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from engine.ledger import LedgerError, apply, open_account
from engine.parse import parse_message
from datetime import date


_TOKEN_TTL = 60


def build_app(dsn, verify):
    app = FastAPI()
    cache = {}

    def identity(request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return None
        token = header.split(" ", 1)[1]
        key = hashlib.sha256(token.encode()).hexdigest()
        cached = cache.get(key)
        if cached and time.monotonic() - cached[1] < _TOKEN_TTL:
            return cached[0]
        user = verify(token)
        if user:
            cache[key] = (user, time.monotonic())
        return user

    def connect(user):
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cur:
            cur.execute("set local role authenticated")
            cur.execute(
                "select set_config('request.jwt.claim.sub', %s, true)", (user,)
            )
        return conn

    @app.post("/accounts")
    def accounts(body: dict, request: Request):
        user = identity(request)
        if not user:
            return JSONResponse({"code": "unauthenticated", "message": "sign in first"}, 401)
        with connect(user) as conn:
            open_account(conn, body["name"], body["currency"], body["opening_balance"],
                         is_default=True)
        return {"status": "ok"}

    @app.post("/chat")
    def chat(body: dict, request: Request):
        user = identity(request)
        if not user:
            return JSONResponse({"code": "unauthenticated", "message": "sign in first"}, 401)
        parsed = parse_message(body["message"], date.today())
        try:
            with connect(user) as conn:
                apply(conn, {
                    "type": "expense",
                    "account": parsed.account,
                    "amount": parsed.amount,
                    "currency": parsed.currency or "INR",
                    "category": parsed.merchant or "general",
                    "date": parsed.date or date.today(),
                    "raw_text": body["message"],
                })
                with conn.cursor() as cur:
                    cur.execute("select current_balance from account_records limit 1")
                    balance = cur.fetchone()[0]
        except LedgerError as error:
            return JSONResponse({"code": error.code, "message": str(error)}, 422)
        return {"balance": balance}

    @app.get("/balances")
    def balances(request: Request):
        user = identity(request)
        if not user:
            return JSONResponse({"code": "unauthenticated", "message": "sign in first"}, 401)
        return {"balances": []}

    return app
