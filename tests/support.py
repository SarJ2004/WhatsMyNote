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


LEGACY = Path(__file__).resolve().parent / "legacy_schema.sql"
SCHEMAS = ("fresh", "legacy")


def reset_schema(dsn=DSN, schema="fresh"):
    """Drop and rebuild the schema, then apply every migration after it.

    fresh is a new database built by 0001. legacy is staging as the old backend
    left it, where 0001 never ran and only the later migrations apply.
    """
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        # 0001 rebuilds the tables it created; later tables are dropped here.
        cur.execute("drop table if exists model_usage")
        if schema == "legacy":
            cur.execute(LEGACY.read_text())
            migrations = [m for m in MIGRATIONS if not m.name.startswith("0001")]
        else:
            migrations = MIGRATIONS
        for migration in migrations:
            cur.execute(migration.read_text())
    conn.close()


def role(conn, user_id):
    """Set the transaction role the way the engine does, or the policies never fire."""
    with conn.cursor() as cur:
        cur.execute("set local role authenticated")
        cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (user_id,))
