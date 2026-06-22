from models.query_plan_model import QueryPlan
from db.config import SessionLocal
from services.record_resolver import resolve_records


def _net_balance(records):
    balance = 0

    for record in records:
        if record.direction == "lent":
            balance += record.amount
        elif record.direction == "borrowed":
            balance -= record.amount

    return balance


def query_executor(state):
    extraction: QueryPlan = state.extraction
    db = SessionLocal()

    try:
        match extraction.operation:

            case "list":
                state.query_result = resolve_records(
                    db,
                    people=extraction.people,
                    filters=extraction.filters,
                )

            case "count":
                records = resolve_records(
                    db,
                    people=extraction.people,
                    filters=extraction.filters,
                )

                state.query_result = len(records)

            case "sum":
                records = resolve_records(
                    db,
                    people=extraction.people,
                    filters=extraction.filters,
                )

                if extraction.metric == "lent":
                    total = sum(r.amount for r in records if r.direction == "lent")

                elif extraction.metric == "borrowed":
                    total = sum(r.amount for r in records if r.direction == "borrowed")

                elif extraction.metric == "outstanding":
                    total = _net_balance(records)

                else:  # all
                    total = sum(r.amount for r in records)

                state.query_result = total

            case "net_balance":
                if len(extraction.people) != 1:
                    state.error = "Net balance queries require exactly one person."
                    return state

                records = resolve_records(
                    db,
                    people=extraction.people,
                    filters=extraction.filters,
                )

                state.query_result = _net_balance(records)

            case "difference":
                if len(extraction.people) != 2:
                    state.error = "Difference queries require exactly two people."
                    return state

                person_a = extraction.people[0]
                person_b = extraction.people[1]

                records_a = resolve_records(
                    db,
                    people=[person_a],
                    filters=extraction.filters,
                )

                records_b = resolve_records(
                    db,
                    people=[person_b],
                    filters=extraction.filters,
                )

                balance_a = _net_balance(records_a)
                balance_b = _net_balance(records_b)

                state.query_result = {
                    person_a: balance_a,
                    person_b: balance_b,
                    "difference": abs(balance_a - balance_b),
                }

            case _:
                state.error = f"Unsupported operation: {extraction.operation}"

        return state

    finally:
        db.close()
