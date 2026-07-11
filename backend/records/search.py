"""Fuzzy search — find records by keyword for HITL interactive selection."""

from __future__ import annotations

from backend.db.config import SessionLocal
from backend.db.schema import (
    BaseRecord, ExpenseRecord, IncomeRecord, LendingRecord,
    TransferRecord, AccountRecord, BudgetRecord,
)
from sqlalchemy.orm import joinedload


_TYPE_TO_ORM = {
    "expense": ExpenseRecord,
    "income": IncomeRecord,
    "lending": LendingRecord,
    "transfer": TransferRecord,
    "account": AccountRecord,
    "budget": BudgetRecord,
}


def _record_to_display_dict(record_type: str, record) -> dict:
    """Convert an ORM record to a human-readable dict for display."""
    base = {"id": record.record_id}

    match record_type:
        case "expense":
            base.update({
                "amount": record.amount,
                "category": record.category,
                "merchant": record.merchant,
                "item": record.item,
                "date": str(record.expense_date) if record.expense_date else None,
                "source": record.payment_source,
            })
        case "income":
            base.update({
                "amount": record.amount,
                "source": record.source,
                "deposit_account": record.deposit_account,
                "date": str(record.income_date) if record.income_date else None,
            })
        case "lending":
            base.update({
                "person": record.person,
                "amount": record.amount,
                "direction": record.direction.value if record.direction else None,
                "account": record.account,
            })
        case "transfer":
            base.update({
                "amount": record.amount,
                "from": record.source_account,
                "to": record.destination_account,
                "date": str(record.transfer_date) if record.transfer_date else None,
            })
        case "account":
            base.update({
                "name": record.name,
                "balance": record.current_balance,
                "default": record.is_default,
            })
        case "budget":
            base.update({
                "category": record.category,
                "limit": record.amount,
                "period": record.period,
            })

    return {k: (v if v is not None else "-") for k, v in base.items()}


def search_recent_records(record_type: str, limit: int = 1000) -> list[dict]:
    """Return the most recent records of a given type for interactive selection."""
    orm_cls = _TYPE_TO_ORM.get(record_type)
    if orm_cls is None:
        return []

    db = SessionLocal()
    try:
        records = (
            db.query(orm_cls)
            .join(BaseRecord)
            .options(joinedload(orm_cls.record))
            .order_by(BaseRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_record_to_display_dict(record_type, r) for r in records]
    finally:
        db.close()
