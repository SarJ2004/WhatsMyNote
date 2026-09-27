"""The HTTP surface. Identity comes from the verified token and is applied as
the transaction role; nothing in a request body can name a user.
"""

import hashlib
import time

import psycopg2
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from engine.ledger import LedgerError, apply, open_account
from engine.parse import parse_message
from engine.queries import balances as query_balances
from engine.queries import spending_by_category
from datetime import date


_TOKEN_TTL = 60


def build_app(dsn, verify):
    app = FastAPI()
    cache = {}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/")
    def site():
        page = Path(__file__).resolve().parents[1] / "web" / "index.html"
        return FileResponse(page)

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
        with connect(user) as conn:
            return {"balances": query_balances(conn)}

    @app.get("/spending")
    def spending(request: Request, start: str, end: str):
        user = identity(request)
        if not user:
            return JSONResponse({"code": "unauthenticated", "message": "sign in first"}, 401)
        with connect(user) as conn:
            rows = spending_by_category(conn, start, end)
        return {"spending": [{"category": category, "converted_minor": amount} for category, amount in rows]}

    @app.get("/records")
    def records(request: Request, type: str = "", start: str = "", end: str = "", q: str = ""):
        user = identity(request)
        if not user:
            return JSONResponse({"code": "unauthenticated", "message": "sign in first"}, 401)
        clauses = ["1=1"]
        params = []
        if type:
            clauses.append("r.record_type = %s")
            params.append(type)
        if start:
            clauses.append("r.created_at::date >= %s")
            params.append(start)
        if end:
            clauses.append("r.created_at::date <= %s")
            params.append(end)
        if q:
            clauses.append("r.raw_text ilike %s")
            params.append("%" + q + "%")
        with connect(user) as conn, conn.cursor() as cur:
            cur.execute(
                "select r.created_at::date, r.record_type, r.raw_text "
                "from records r where " + " and ".join(clauses) + " order by r.created_at desc",
                params,
            )
            rows = [
                {"date": str(row[0]), "record_type": row[1], "raw_text": row[2]}
                for row in cur.fetchall()
            ]
        return {"records": rows}

    return app


def _live_verify(token):
    import os
    from supabase import create_client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    client = create_client(url, key)
    result = client.auth.get_user(token)
    if not result or not result.user:
        return None
    return result.user.id


def create_live_app():
    """The process Render starts. Tests build their own app and never call this."""
    import os

    database_url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    return build_app(database_url, _live_verify)
