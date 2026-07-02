from db.config import SessionLocal
from records.budget.models import QueryBudget
from records.budget.resolver import resolve_records


def query_executor(state):
    extraction: QueryBudget = state.extraction
    db = SessionLocal()
    try:
        records = resolve_records(
            db, categories=extraction.categories, filters=extraction.filters
        )
        if extraction.operation == "list":
            state.query_result = records
        elif extraction.operation == "count":
            state.query_result = len(records)
        elif extraction.operation == "sum":
            state.query_result = sum(r.amount for r in records)
        elif extraction.operation == "average":
            state.query_result = (
                sum(r.amount for r in records) / len(records) if records else 0
            )
        elif extraction.operation == "max":
            state.query_result = (
                max(records, key=lambda r: r.amount) if records else None
            )
        elif extraction.operation == "min":
            state.query_result = (
                min(records, key=lambda r: r.amount) if records else None
            )
        elif extraction.operation == "remaining":
            state.query_result = {r.category: r.amount for r in records}
        elif extraction.operation == "variance":
            state.query_result = {r.category: r.amount for r in records}
        else:
            state.error = f"Unsupported operation: {extraction.operation}"
        return state
    finally:
        db.close()
