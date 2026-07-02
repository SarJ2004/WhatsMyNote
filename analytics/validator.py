import re


FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|merge|call|execute|exec|into\s+outfile|load_file)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str, allowed_tables: list[str]) -> None:
    candidate = sql.strip()

    if ";" in candidate:
        raise ValueError("Multiple statements are not allowed.")

    if not re.match(r"^(with|select)\b", candidate, re.IGNORECASE):
        raise ValueError("Only SELECT or WITH queries are allowed.")

    if FORBIDDEN.search(candidate):
        raise ValueError("Dangerous SQL detected.")

    if "--" in candidate or "/*" in candidate or "*/" in candidate:
        raise ValueError("SQL comments are not allowed.")

    lower = candidate.lower()
    for table in ["records", "lending_records", "expense_records", "income_records", "transfer_records"]:
        if table in lower and table not in allowed_tables:
            raise ValueError(f"Table not allowed for this question: {table}")