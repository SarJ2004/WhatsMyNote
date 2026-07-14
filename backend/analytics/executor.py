import re

from sqlalchemy import text

from backend.analytics.planner import plan_sql
from backend.analytics.verifier import review_sql_result
from backend.analytics.validator import validate_sql
from backend.db.config import SessionLocal


MAX_ANALYTICS_RETRIES = 3

NET_WORTH_PATTERN = re.compile(
    r"\b(net\s*worth|total\s*balance|total\s*assets)\b", re.IGNORECASE
)


def _execute_sql(db, sql: str):
    result = db.execute(text(sql))
    rows = result.mappings().all()

    if len(rows) == 1 and len(rows[0]) == 1:
        return next(iter(rows[0].values()))

    return [dict(row) for row in rows]


def analytics_query_executor(state):
    question = state.get("raw_text", "")

    db = SessionLocal()

    try:
        # Fast-path: net worth — deterministic, no LLM SQL needed
        if NET_WORTH_PATTERN.search(question):
            sql = "SELECT SUM(current_balance) AS net_worth FROM account_records"
            query_result = _execute_sql(db, sql)
            return {
                "query_result": query_result,
                "analytics_sql": sql,
                "analytics_review": "Net worth computed as sum of all account current balances."
            }

        sql, chart_config, allowed_tables = plan_sql(question)

        review_notes: list[str] = []
        final_query_result = None
        final_sql = sql
        final_review = None

        for attempt in range(1, MAX_ANALYTICS_RETRIES + 1):
            try:
                validate_sql(sql, allowed_tables, db=db)
            except ValueError as exc:
                return {"error": f"Could not generate a valid query: {exc}"}

            try:
                query_result = _execute_sql(db, sql)
            except Exception as exc:
                return {"error": f"Query execution failed: {exc}"}

            review = review_sql_result(question, sql, query_result, chart_config=chart_config)

            note = f"Attempt {attempt}: {review.reason} (confidence {review.confidence}%)"
            if review.rationale:
                note = f"{note} {review.rationale}"
            review_notes.append(note)

            final_query_result = query_result
            final_sql = sql
            final_review = note

            if review.revised_chart_config:
                from backend.analytics.models import ChartConfig
                try:
                    chart_config = ChartConfig(**review.revised_chart_config)
                except Exception:
                    chart_config = review.revised_chart_config

            if review.approved:
                break

            if not review.revised_sql or review.revised_sql.strip() == sql.strip():
                break

            sql = review.revised_sql.strip()

        if review_notes:
            final_review = review_notes[-1]

        # Convert chart_config to dict for state
        chart_config_dict = None
        if chart_config:
            if hasattr(chart_config, "model_dump"):
                chart_config_dict = chart_config.model_dump()
            else:
                chart_config_dict = chart_config

        return {
            "query_result": final_query_result,
            "analytics_sql": final_sql,
            "analytics_review": final_review,
            "chart_config": chart_config_dict,
        }

    except Exception as exc:
        return {"error": f"Analytics query failed: {exc}"}

    finally:
        db.close()
