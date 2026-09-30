"""Shared test helpers. Every test database is built from the committed migrations."""

import os
from pathlib import Path

import psycopg2

DSN = os.environ.get(
    "WMN_TEST_DSN", "postgresql://postgres:wmn@localhost:54329/whatsmynote"
)
ALICE = "11111111-1111-1111-1111-111111111111"
BOB = "22222222-2222-2222-2222-222222222222"
MIGRATIONS = sorted((Path(__file__).resolve().parents[1] / "supabase" / "migrations").glob("*.sql"))


def reset_schema(dsn=DSN):
    """Drop and rebuild the schema by applying every migration in order."""
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        # 0001 rebuilds the tables it created; later tables are dropped here.
        cur.execute("drop table if exists model_usage")
        for migration in MIGRATIONS:
            cur.execute(migration.read_text())
    conn.close()


def role(conn, user_id):
    """Set the transaction role the way the engine does, or the policies never fire."""
    with conn.cursor() as cur:
        cur.execute("set local role authenticated")
        cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (user_id,))
