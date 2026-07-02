from sqlalchemy import text

from analytics.planner import plan_sql
from analytics.validator import validate_sql
from db.config import SessionLocal


def analytics_query_executor(state):
    sql, allowed_tables = plan_sql(state.raw_text)
    validate_sql(sql, allowed_tables)

    db = SessionLocal()

    try:
        result = db.execute(text(sql))
        rows = result.mappings().all()

        if len(rows) == 1 and len(rows[0]) == 1:
            state.query_result = next(iter(rows[0].values()))
        else:
            state.query_result = [dict(row) for row in rows]

        state.analytics_sql = sql
        return state

    finally:
        db.close()
