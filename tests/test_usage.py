from datetime import date

from engine.db import Database
from engine.usage import take
from tests.support import ALICE, BOB

DAY = date(2026, 9, 26)


def test_calls_are_allowed_up_to_the_daily_ceiling_per_user(dsn):
    db = Database(dsn, size=1)
    try:
        assert [take(db, ALICE, 2, DAY) for _ in range(3)] == [True, True, False]
        assert take(db, BOB, 2, DAY)
        assert take(db, ALICE, 2, date(2026, 9, 27))
    finally:
        db.close()


def test_a_ceiling_of_zero_allows_no_calls(dsn):
    db = Database(dsn, size=1)
    try:
        assert not take(db, ALICE, 0, DAY)
    finally:
        db.close()
