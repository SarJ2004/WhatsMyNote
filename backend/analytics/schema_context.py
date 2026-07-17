SCHEMA = {
    "records": {
        "id": "INTEGER PRIMARY KEY",
        "record_type": "VARCHAR, enum: 'expense', 'income', 'transfer', 'lending', 'account', 'budget'",
        "raw_text": "VARCHAR, the original user input",
        "created_at": "TIMESTAMP, when the record was created",
        "updated_at": "TIMESTAMP, when the record was last updated",
    },
    "lending_records": {
        "record_id": "INTEGER PRIMARY KEY, foreign key to records.id",
        "person": "VARCHAR, the person who lent you money or borrowed money from you",
        "source_account": "VARCHAR, the account used for lending/borrowing",
        "amount": "FLOAT, the amount lent or borrowed",
        "direction": "VARCHAR, ONLY 'LENT' (you gave them money) or 'BORROWED' (they gave you money, e.g. paying you back or lending to you)",
        "expected_payback_by": "DATE, when the money should be returned",
    },
    "expense_records": {
        "record_id": "INTEGER PRIMARY KEY, foreign key to records.id",
        "amount": "FLOAT, the cost of the expense",
        "category": "VARCHAR, budget category (e.g., food, utilities, rent)",
        "merchant": "VARCHAR, where the money was spent or to whom",
        "payment_source": "VARCHAR, the account used to pay",
        "expense_date": "DATE, when the expense occurred",
        "item": "VARCHAR, specific item bought",
        "notes": "VARCHAR, additional details",
    },
    "account_records": {
        "record_id": "INTEGER PRIMARY KEY, foreign key to records.id",
        "name": "VARCHAR, the name of the bank or account",
        "opening_balance": "FLOAT, the starting balance",
        "current_balance": "FLOAT, the LIVE computed current balance. Do NOT calculate balance manually from transactions, just use this column.",
        "currency": "VARCHAR, the currency (e.g., USD, INR)",
        "notes": "VARCHAR, additional details",
    },
    "budget_records": {
        "record_id": "INTEGER PRIMARY KEY, foreign key to records.id",
        "category": "VARCHAR, the budget category (e.g. 'Overall', 'Food')",
        "amount": "FLOAT, the maximum limit for this budget",
        "period": "VARCHAR, timeframe (e.g., monthly, weekly)",
        "budget_date": "DATE, when the budget starts",
        "notes": "VARCHAR, additional details",
    },
    "income_records": {
        "record_id": "INTEGER PRIMARY KEY, foreign key to records.id",
        "source": "VARCHAR, who or what paid the user (e.g., salary, employer, a person's name)",
        "deposit_account": "VARCHAR, the account the money was deposited into",
        "amount": "FLOAT, the amount of income",
        "income_date": "DATE, when the income was received",
        "notes": "VARCHAR, additional details",
    },
    "transfer_records": {
        "record_id": "INTEGER PRIMARY KEY, foreign key to records.id",
        "source_account": "VARCHAR, account money was taken from",
        "destination_account": "VARCHAR, account money was sent to",
        "amount": "FLOAT, the amount transferred",
        "transfer_date": "DATE, when the transfer occurred",
        "notes": "VARCHAR, additional details",
    },
}


def select_tables(question: str) -> list[str]:
    # Expose full schema to read-only SQL planner so any valid query can span
    # all supported tables without hardcoded table gating.
    return list(SCHEMA.keys())


def schema_context_for_question(question: str) -> str:
    tables = select_tables(question)
    lines = []

    for table in tables:
        lines.append(f"Table: {table}")
        for col, desc in SCHEMA[table].items():
            lines.append(f"  - {col}: {desc}")
        lines.append("")

    return "\n".join(lines)
