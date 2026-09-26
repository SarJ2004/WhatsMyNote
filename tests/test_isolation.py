import os

import psycopg2
import pytest

DSN = os.environ.get(
    "WMN_TEST_DSN", "postgresql://postgres:wmn@localhost:54329/whatsmynote"
)


def apply_role(conn, user_id):
    """Set the transaction role the way the engine does, or the policies never fire."""
    with conn.cursor() as cur:
        cur.execute("set local role authenticated")
        cur.execute("select set_config('request.jwt.claim.sub', %s, true)", (user_id,))


@pytest.fixture
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(open("supabase/migrations/0001_isolation.sql").read())
    yield conn
    conn.close()


def test_another_users_row_is_invisible_and_untouchable(db):
    with db:
        apply_role(db, "11111111-1111-1111-1111-111111111111")
        with db.cursor() as cur:
            cur.execute(
                "insert into records (user_id, record_type, raw_text) "
                "values (%s, 'expense', 'lunch') returning id",
                ("11111111-1111-1111-1111-111111111111",),
            )
            row_id = cur.fetchone()[0]

    with db:
        apply_role(db, "22222222-2222-2222-2222-222222222222")
        with db.cursor() as cur:
            cur.execute("select id from records where id = %s", (row_id,))
            assert cur.fetchall() == []
            cur.execute(
                "update records set raw_text = 'stolen' where id = %s", (row_id,)
            )
            assert cur.rowcount == 0
