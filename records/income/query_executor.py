from db.config import SessionLocal
from records.income.models import QueryIncome
from records.income.resolver import resolve_records


def query_executor(state):
    extraction: QueryIncome = state.extraction
    db = SessionLocal()

    try:
        records = resolve_records(
            db,
            sources=extraction.sources,
            filters=extraction.filters,
        )

        match extraction.operation:
            case "list":
                state.query_result = records

            case "count":
                state.query_result = len(records)

            case "sum":
                state.query_result = sum(r.amount for r in records)

            case "average":
                state.query_result = sum(r.amount for r in records) / len(records) if records else 0

            case "max":
                state.query_result = max(records, key=lambda r: r.amount) if records else None

            case "min":
                state.query_result = min(records, key=lambda r: r.amount) if records else None

            case _:
                state.error = f"Unsupported operation: {extraction.operation}"

        return state

    finally:
        db.close()