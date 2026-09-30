import psycopg2
import pytest

from tests.support import DSN, reset_schema


@pytest.fixture
def dsn():
    reset_schema(DSN)
    return DSN


@pytest.fixture
def conn(dsn):
    c = psycopg2.connect(dsn)
    c.autocommit = True
    yield c
    c.close()
