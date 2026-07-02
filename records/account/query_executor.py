from db.config import SessionLocal
from records.account.models import QueryAccount
from records.account.resolver import resolve_records, current_balance


def _record_view(db, record):
    balance = current_balance(db, record.name)
    return {
        "name": record.name,
        "opening_balance": record.opening_balance,
        "current_balance": balance,
        "currency": record.currency,
        "notes": record.notes,
    }


def query_executor(state):
    extraction: QueryAccount = state.extraction
    db = SessionLocal()

    try:
        records = resolve_records(
            db, accounts=extraction.accounts, filters=extraction.filters
        )
        balances = [_record_view(db, record) for record in records]

        match extraction.operation:
            case "list":
                state.query_result = balances
            case "count":
                state.query_result = len(balances)
            case "sum":
                state.query_result = sum(
                    item["current_balance"] or 0 for item in balances
                )
            case "average":
                state.query_result = (
                    (
                        sum(item["current_balance"] or 0 for item in balances)
                        / len(balances)
                    )
                    if balances
                    else 0
                )
            case "max":
                state.query_result = (
                    max(balances, key=lambda item: item["current_balance"] or 0)
                    if balances
                    else None
                )
            case "min":
                state.query_result = (
                    min(balances, key=lambda item: item["current_balance"] or 0)
                    if balances
                    else None
                )
            case "balance":
                if extraction.accounts:
                    if len(balances) == 1:
                        state.query_result = balances[0]["current_balance"]
                    else:
                        state.query_result = {
                            item["name"]: item["current_balance"] for item in balances
                        }
                else:
                    state.query_result = balances
            case _:
                state.error = f"Unsupported operation: {extraction.operation}"

        return state
    finally:
        db.close()
