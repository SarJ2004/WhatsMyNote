from records.expense.models import QueryExpense
from db.config import SessionLocal
from records.expense.resolver import resolve_records


def query_executor(state):
    extraction: QueryExpense = state.extraction
    db = SessionLocal()

    try:
        records = resolve_records(
            db,
            categories=extraction.categories,
            merchants=extraction.merchants,
            payment_sources=extraction.payment_sources,
            items=extraction.items,
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
                if records:
                    state.query_result = sum(r.amount for r in records) / len(records)
                else:
                    state.query_result = 0

            case "max":
                state.query_result = (
                    max(records, key=lambda r: r.amount) if records else None
                )

            case "min":
                state.query_result = (
                    min(records, key=lambda r: r.amount) if records else None
                )

            case _:
                state.error = f"Unsupported operation: {extraction.operation}"

        print(state.extraction)
        return state

    finally:
        db.close()
