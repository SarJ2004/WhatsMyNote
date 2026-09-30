"""Pooled connections, one transaction per use.

A user transaction opens, sets the role and the user claim, and bounds its own
run time in a single round trip, and all of it ends with the transaction, so a
connection returned to the pool carries nothing of the user who last held it.
Connections run in autocommit mode and each transaction is opened and closed
explicitly, which saves the separate round trip a driver-issued BEGIN would cost.
Every connection taken is either returned or closed.
"""

import queue
import threading
from contextlib import contextmanager

import psycopg2
import psycopg2.extensions

_BROKEN = (psycopg2.OperationalError, psycopg2.InterfaceError)
_USER_SETUP = (
    "begin; "
    "set local role authenticated; "
    "set local statement_timeout = '10s'; "
    "set local lock_timeout = '5s'; "
    "select set_config('request.jwt.claim.sub', %s, true)"
)
_SERVICE_SETUP = "begin; set local statement_timeout = '5s'"


class _Connection(psycopg2.extensions.connection):
    # The user the open transaction runs as, so the ledger need not ask the server.
    user_id = None


class Database:
    def __init__(self, dsn, size=5, timeout=10.0, application_name="whatsmynote"):
        self._dsn = dsn
        self._timeout = timeout
        self._application_name = application_name
        self._idle = queue.LifoQueue()
        self._slots = threading.BoundedSemaphore(size)
        self._closed = False

    @contextmanager
    def user(self, user_id):
        """A transaction that sees and writes only this user's rows."""
        with self._transaction(_USER_SETUP, (user_id,), user_id) as conn:
            yield conn

    @contextmanager
    def service(self):
        """A transaction as the engine itself, for the rate cache and usage counters."""
        with self._transaction(_SERVICE_SETUP, None, None) as conn:
            yield conn

    def service_one(self, statement, params):
        """One statement as the engine itself, committed on its own, in one round trip.
        The first row it returns, or None."""
        conn = self._take()
        broken = False
        try:
            try:
                return _fetch_one(conn, statement, params)
            except _BROKEN:
                conn.close()
                conn = self._open()
                return _fetch_one(conn, statement, params)
        except _BROKEN:
            broken = True
            raise
        finally:
            self._give(conn, broken)

    def close(self):
        self._closed = True
        while True:
            try:
                self._idle.get_nowait().close()
            except queue.Empty:
                return

    def _open(self):
        conn = psycopg2.connect(self._dsn, application_name=self._application_name,
                                connection_factory=_Connection)
        conn.autocommit = True
        return conn

    def _take(self):
        if not self._slots.acquire(timeout=self._timeout):
            raise RuntimeError("no database connection became free in time")
        try:
            return self._idle.get_nowait()
        except queue.Empty:
            pass
        try:
            return self._open()
        except BaseException:
            self._slots.release()
            raise

    def _give(self, conn, broken):
        conn.user_id = None
        if broken or conn.closed or self._closed:
            conn.close()
        else:
            self._idle.put(conn)
        self._slots.release()

    @contextmanager
    def _transaction(self, setup, params, user_id):
        conn = self._take()
        broken = False
        try:
            try:
                _send(conn, setup, params)
            except _BROKEN:
                # The server dropped this idle connection. Nothing has run in the
                # transaction yet, so a fresh connection is safe to use instead.
                conn.close()
                conn = self._open()
                _send(conn, setup, params)
            conn.user_id = user_id
            yield conn
            _send(conn, "commit")
        except BaseException as error:
            broken = isinstance(error, _BROKEN)
            if not conn.closed:
                try:
                    _send(conn, "rollback")
                except _BROKEN:
                    broken = True
            raise
        finally:
            self._give(conn, broken)


def _send(conn, statement, params=None):
    with conn.cursor() as cur:
        cur.execute(statement, params)


def _fetch_one(conn, statement, params):
    with conn.cursor() as cur:
        cur.execute(statement, params)
        return cur.fetchone() if cur.description else None
