import threading
import uuid

import psycopg2
import pytest

from engine.db import Database
from tests.support import ALICE


def _open_connections(dsn, name):
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            "select count(*) from pg_stat_activity where application_name = %s", (name,)
        )
        count = cur.fetchone()[0]
    conn.close()
    return count


@pytest.fixture
def database(dsn):
    name = "wmn-test-" + uuid.uuid4().hex[:8]
    db = Database(dsn, size=2, application_name=name)
    yield db, name
    db.close()


def test_a_user_transaction_runs_as_that_user(database):
    db, _ = database
    with db.user(ALICE) as conn, conn.cursor() as cur:
        cur.execute("select current_user, current_setting('request.jwt.claim.sub')")
        assert cur.fetchone() == ("authenticated", ALICE)


def test_the_role_does_not_outlive_the_transaction(database):
    db, _ = database
    with db.user(ALICE):
        pass
    with db.service() as conn, conn.cursor() as cur:
        cur.execute("select current_user, current_setting('request.jwt.claim.sub', true)")
        user, claim = cur.fetchone()
    assert user != "authenticated"
    assert not claim


def test_connections_are_reused_rather_than_opened_per_request(dsn, database):
    db, name = database
    for _ in range(20):
        with db.user(ALICE) as conn, conn.cursor() as cur:
            cur.execute("select 1")
    assert _open_connections(dsn, name) == 1


def test_a_failed_transaction_rolls_back_and_the_connection_stays_usable(database):
    db, _ = database
    with pytest.raises(RuntimeError):
        with db.user(ALICE) as conn, conn.cursor() as cur:
            cur.execute(
                "insert into records (user_id, record_type, raw_text) "
                "values (%s, 'EXPENSE', 'lunch')", (ALICE,)
            )
            raise RuntimeError("boom")
    with db.user(ALICE) as conn, conn.cursor() as cur:
        cur.execute("select count(*) from records")
        assert cur.fetchone()[0] == 0


def test_a_connection_the_server_dropped_is_replaced(dsn, database):
    db, name = database
    with db.user(ALICE):
        pass
    killer = psycopg2.connect(dsn)
    killer.autocommit = True
    with killer.cursor() as cur:
        cur.execute(
            "select pg_terminate_backend(pid) from pg_stat_activity "
            "where application_name = %s", (name,)
        )
    killer.close()
    with db.user(ALICE) as conn, conn.cursor() as cur:
        cur.execute("select 1")
        assert cur.fetchone()[0] == 1


def test_concurrent_requests_wait_for_a_connection_instead_of_failing(dsn, database):
    db, name = database
    errors = []
    peak = []

    def work():
        try:
            with db.user(ALICE) as conn, conn.cursor() as cur:
                cur.execute("select pg_sleep(0.05)")
                peak.append(_open_connections(dsn, name))
        except Exception as error:  # pragma: no cover - the assertion reports it
            errors.append(error)

    threads = [threading.Thread(target=work) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert max(peak) <= 2


def test_close_releases_every_connection(dsn, database):
    db, name = database
    with db.user(ALICE):
        pass
    db.close()
    assert _open_connections(dsn, name) == 0


def test_a_user_transaction_carries_its_user(database):
    db, _ = database
    with db.user(ALICE) as conn:
        assert conn.user_id == ALICE
    with db.service() as conn:
        assert conn.user_id is None


def test_a_transaction_costs_two_round_trips_beyond_its_own_statements(database, monkeypatch):
    import engine.db as module

    db, _ = database
    with db.user(ALICE):
        pass
    sent = []
    original = module._send
    monkeypatch.setattr(module, "_send", lambda conn, sql, params=None: (
        sent.append(sql), original(conn, sql, params))[1])
    with db.user(ALICE) as conn, conn.cursor() as cur:
        cur.execute("select 1")
    assert len(sent) == 2


def test_a_connection_that_cannot_be_opened_frees_its_slot():
    db = Database("postgresql://postgres:wrong@localhost:1/none", size=1, timeout=0.5)
    for _ in range(2):
        with pytest.raises(psycopg2.OperationalError):
            with db.user(ALICE):
                pass


def test_a_connection_dropped_mid_transaction_is_not_reused(dsn, database):
    db, name = database
    killer = psycopg2.connect(dsn)
    killer.autocommit = True
    try:
        with pytest.raises(psycopg2.OperationalError):
            with db.user(ALICE) as conn, conn.cursor() as cur:
                with killer.cursor() as kill:
                    kill.execute("select pg_terminate_backend(%s)", (conn.get_backend_pid(),))
                cur.execute("select 1")
    finally:
        killer.close()
    with db.user(ALICE) as conn, conn.cursor() as cur:
        cur.execute("select 1")
    assert _open_connections(dsn, name) == 1
