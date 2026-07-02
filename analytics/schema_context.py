SCHEMA = {
    "records": ["id", "record_type", "raw_text", "created_at", "updated_at", "settled_at"],
    "lending_records": ["record_id", "person", "amount", "direction", "expected_payback_by"],
    "expense_records": ["record_id", "amount", "category", "merchant", "payment_source", "expense_date", "item", "notes"],
    "income_records": ["record_id", "source", "amount", "income_date", "notes"],
    "transfer_records": ["record_id", "source_account", "destination_account", "amount", "transfer_date", "notes"],
}


def select_tables(question: str) -> list[str]:
    text = question.lower()

    tables = ["records"]

    if any(word in text for word in ["spend", "spent", "expense", "buy", "bought", "merchant", "category", "purchase", "paid"]):
        tables.append("expense_records")

    if any(word in text for word in ["salary", "cashback", "income", "received", "earned", "refund"]):
        tables.append("income_records")

    if any(word in text for word in ["lent", "borrowed", "owe", "owes", "owed", "debt", "outstanding", "repay", "balance", "due"]):
        tables.append("lending_records")

    if any(word in text for word in ["transfer", "transferred", "sent money", "account"]):
        tables.append("transfer_records")

    if "savings" in text or "save" in text:
        for table in ["income_records", "expense_records"]:
            if table not in tables:
                tables.append(table)

    return tables


def schema_context_for_question(question: str) -> str:
    tables = select_tables(question)
    lines = []

    for table in tables:
        columns = ", ".join(SCHEMA[table])
        lines.append(f"{table}({columns})")

    return "\n".join(lines)