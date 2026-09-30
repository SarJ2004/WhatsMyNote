import psycopg2
import pytest

from tests.support import DSN, SCHEMAS, reset_schema


@pytest.fixture(params=SCHEMAS)
def dsn(request):
    """Every database test runs on a fresh database and on staging's legacy schema."""
    reset_schema(DSN, request.param)
    return DSN


@pytest.fixture
def conn(dsn):
    c = psycopg2.connect(dsn)
    c.autocommit = True
    yield c
    c.close()
