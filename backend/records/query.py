"""Generic query executor — handles query operations for all record types."""

from __future__ import annotations

from backend.db.config import SessionLocal
from backend.records.resolver import resolve_records


def _extract_query_kwargs(record_type: str, extraction: dict) -> dict:
    """Extract the filter kwargs from the extraction dict based on record type."""
    kwargs = {}
    match record_type:
        case "expense":
            for key in ("categories", "merchants", "payment_sources", "items"):
                if extraction.get(key):
                    # Map plural filter name to DB column name
                    col_map = {
                        "categories": "category",
                        "merchants": "merchant",
                        "payment_sources": "payment_source",
                        "items": "item",
                    }
                    kwargs[col_map[key]] = extraction[key]
        case "income":
            for key in ("sources", "deposit_accounts"):
                if extraction.get(key):
                    col_map = {"sources": "source", "deposit_accounts": "deposit_account"}
                    kwargs[col_map[key]] = extraction[key]
        case "lending":
            if extraction.get("people"):
                kwargs["person"] = extraction["people"]
        case "transfer":
            if extraction.get("from_accounts"):
                kwargs["source_account"] = extraction["from_accounts"]
            if extraction.get("to_accounts"):
                kwargs["destination_account"] = extraction["to_accounts"]
        case "account":
            if extraction.get("accounts"):
                kwargs["name"] = extraction["accounts"]
        case "budget":
            if extraction.get("categories"):
                kwargs["category"] = extraction["categories"]
    return kwargs


def query_executor(state):
    """Generic query executor node."""
    extraction = state.get("extraction")
    record_type = state.get("record_type")

    if not extraction or not record_type:
        return {"error": "Missing extraction or record type."}

    operation = extraction.get("operation", "list")
    filters = extraction.get("filters")
    kwargs = _extract_query_kwargs(record_type, extraction)

    db = SessionLocal()

    try:
        records = resolve_records(db, record_type, filters=filters, **kwargs)

        match operation:
            case "list":
                return {"query_result": records}
            case "count":
                return {"query_result": len(records)}
            case "sum":
                return {"query_result": sum(getattr(r, "amount", 0) for r in records)}
            case "average":
                if records:
                    return {"query_result": sum(getattr(r, "amount", 0) for r in records) / len(records)}
                return {"query_result": 0}
            case "max":
                if records:
                    return {"query_result": max(records, key=lambda r: getattr(r, "amount", 0))}
                return {"query_result": None}
            case "min":
                if records:
                    return {"query_result": min(records, key=lambda r: getattr(r, "amount", 0))}
                return {"query_result": None}
            case "balance":
                # Special case for accounts
                if records:
                    return {"query_result": [
                        {"name": r.name, "balance": r.current_balance}
                        for r in records
                    ]}
                return {"query_result": []}
            case "difference" | "net_balance":
                # Special case for lending
                lent = sum(getattr(r, "amount", 0) for r in records if getattr(r, "direction", None) and r.direction.value == "lent")
                borrowed = sum(getattr(r, "amount", 0) for r in records if getattr(r, "direction", None) and r.direction.value == "borrowed")
                return {"query_result": {"lent": lent, "borrowed": borrowed, "net": lent - borrowed}}
            case _:
                return {"error": f"Unsupported operation: {operation}"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()
