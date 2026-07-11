SCHEMA = {
    "records": [
        "id",
        "record_type",
        "raw_text",
        "created_at",
        "updated_at",
    ],
    "lending_records": [
        "record_id",
        "person",
        "source_account",
        "amount",
        "direction",
        "expected_payback_by",
    ],
    "expense_records": [
        "record_id",
        "amount",
        "category",
        "merchant",
        "payment_source",
        "expense_date",
        "item",
        "notes",
    ],
    "account_records": [
        "record_id",
        "name",
        "opening_balance",
        "current_balance",
        "currency",
        "notes",
    ],
    "budget_records": [
        "record_id",
        "category",
        "amount",
        "period",
        "budget_date",
        "notes",
    ],
    "income_records": [
        "record_id",
        "source",
        "deposit_account",
        "amount",
        "income_date",
        "notes",
    ],
    "transfer_records": [
        "record_id",
        "source_account",
        "destination_account",
        "amount",
        "transfer_date",
        "notes",
    ],
}


def select_tables(question: str) -> list[str]:
    # Expose full schema to read-only SQL planner so any valid query can span
    # all supported tables without hardcoded table gating.
    return list(SCHEMA.keys())


def schema_context_for_question(question: str) -> str:
    tables = select_tables(question)
    lines = []

    for table in tables:
        columns = ", ".join(SCHEMA[table])
        lines.append(f"{table}({columns})")

    return "\n".join(lines)
