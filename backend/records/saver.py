"""Generic record saver — handles create for all record types."""

from __future__ import annotations

from backend.db.config import SessionLocal
from backend.db.schema import BaseRecord, RecordType
from backend.db.schema import (
    ExpenseRecord, IncomeRecord, LendingRecord,
    TransferRecord, AccountRecord, BudgetRecord,
)
from backend.records.account_utils import get_default_account_name, sync_account_balances
from backend.records.normalization import normalize_label
from backend.budget.alerts import build_budget_alerts_for_expense


def _build_type_record(record_type: str, record_data: dict, default_account: str | None):
    """Build the type-specific ORM record from extraction data."""
    match record_type:
        case "expense":
            return ExpenseRecord(
                amount=record_data["amount"],
                category=normalize_label(record_data.get("category")),
                merchant=normalize_label(record_data.get("merchant")),
                payment_source=normalize_label(record_data.get("payment_source")) or default_account,
                item=normalize_label(record_data.get("item")),
                expense_date=record_data.get("expense_date"),
                notes=record_data.get("notes"),
            )
        case "income":
            return IncomeRecord(
                amount=record_data["amount"],
                source=normalize_label(record_data.get("source")) or "Unknown",
                deposit_account=normalize_label(record_data.get("deposit_account")) or default_account,
                income_date=record_data.get("income_date"),
                notes=record_data.get("notes"),
            )
        case "lending":
            return LendingRecord(
                person=normalize_label(record_data.get("person")) or "Unknown",
                account=normalize_label(record_data.get("account")) or default_account,
                amount=record_data["amount"],
                direction=record_data.get("direction", "lent"),
                expected_payback_by=record_data.get("expected_payback_by"),
            )
        case "transfer":
            return TransferRecord(
                source_account=normalize_label(record_data.get("source_account")) or default_account,
                destination_account=normalize_label(record_data.get("destination_account")) or "Unknown",
                amount=record_data["amount"],
                transfer_date=record_data.get("transfer_date"),
                notes=record_data.get("notes"),
            )
        case "account":
            return AccountRecord(
                name=normalize_label(record_data.get("name")) or "Unknown",
                is_default=record_data.get("is_default", False),
                opening_balance=record_data.get("opening_balance", 0),
                current_balance=record_data.get("opening_balance", 0),
                currency=record_data.get("currency"),
                notes=record_data.get("notes"),
            )
        case "budget":
            return BudgetRecord(
                category=normalize_label(record_data.get("category")) or "Overall",
                amount=record_data["amount"],
                period=record_data.get("period", "monthly"),
                budget_date=record_data.get("budget_date"),
                notes=record_data.get("notes"),
            )
        case _:
            raise ValueError(f"Unknown record type: {record_type}")


_RECORD_TYPE_ENUM = {
    "expense": RecordType.EXPENSE,
    "income": RecordType.INCOME,
    "lending": RecordType.LENDING,
    "transfer": RecordType.TRANSFER,
    "account": RecordType.ACCOUNT,
    "budget": RecordType.BUDGET,
}

_TYPE_RELATIONSHIP = {
    "expense": "expense",
    "income": "income",
    "lending": "lending",
    "transfer": "transfer",
    "account": "account",
    "budget": "budget",
}


def record_saver(state):
    """Generic saver node — dispatches based on state.get("record_type")."""
    extraction = state.get("extraction")
    record_type = state.get("record_type")

    if not extraction or not record_type:
        return {"error": "Missing extraction or record type."}

    records_data = extraction.get("records", [])
    if not records_data:
        return {"error": "No records to save."}

    db = SessionLocal()
    saved_ids = []

    try:
        default_account = get_default_account_name(db)

        for record_data in records_data:
            if isinstance(record_data, dict):
                data = record_data
            else:
                data = record_data.model_dump() if hasattr(record_data, "model_dump") else dict(record_data)

            base_record = BaseRecord(
                record_type=_RECORD_TYPE_ENUM[record_type],
                raw_text=state.get("raw_text"),
            )
            type_record = _build_type_record(record_type, data, default_account)
            setattr(base_record, _TYPE_RELATIONSHIP[record_type], type_record)

            if record_type == "budget":
                # Check for existing budget with same category
                cat = type_record.category
                existing_budget = db.query(BudgetRecord).filter(BudgetRecord.category == cat).first()
                if existing_budget:
                    existing_budget.amount = type_record.amount
                    if type_record.period != "monthly":
                        existing_budget.period = type_record.period
                    if type_record.notes:
                        existing_budget.notes = type_record.notes
                    # We updated existing, so don't create a new BaseRecord for it
                    db.flush()
                    saved_ids.append(existing_budget.record_id)
                    continue

            db.add(base_record)
            db.flush()
            saved_ids.append(base_record.id)

        db.commit()

        # Budget alerts for expenses
        alerts = []
        if record_type == "expense":
            from backend.db.schema import ExpenseRecord
            db.expire_all()
            for record_id in saved_ids:
                expense = db.get(ExpenseRecord, record_id)
                if expense is not None:
                    alerts.extend(build_budget_alerts_for_expense(db, expense))

        sync_account_balances(db)
        db.commit()

    except Exception as e:
        db.rollback()
        return {"error": f"Failed to save records: {e}"}
    finally:
        db.close()

    return {
        "saved_record_ids": saved_ids,
        "budget_alerts": sorted(set(alerts)) if alerts else [],
    }
