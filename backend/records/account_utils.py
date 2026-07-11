"""Account utilities — balance sync and default account management."""

from __future__ import annotations

from sqlalchemy import func

from backend.db.schema import (
    AccountRecord,
    ExpenseRecord,
    IncomeRecord,
    LendingDirection,
    LendingRecord,
    TransferRecord,
)


# ── Default account ────────────────────────────────────────────

def get_default_account_name(db) -> str | None:
    record = db.query(AccountRecord).filter(AccountRecord.is_default.is_(True)).first()
    return record.name if record else None


def set_default_account_name(db, account_name: str | None) -> None:
    db.query(AccountRecord).update({AccountRecord.is_default: False})
    if not account_name:
        return
    record = db.query(AccountRecord).filter(AccountRecord.name == account_name).first()
    if record is not None:
        record.is_default = True


# ── Balance sync ───────────────────────────────────────────────

def sync_account_balances(db) -> None:
    """Recompute current_balance for every account from transaction history."""
    accounts = db.query(AccountRecord).all()

    for account in accounts:
        balance = account.opening_balance or 0

        incoming_transfers = (
            db.query(func.coalesce(func.sum(TransferRecord.amount), 0))
            .filter(TransferRecord.destination_account == account.name)
            .scalar() or 0
        )
        outgoing_transfers = (
            db.query(func.coalesce(func.sum(TransferRecord.amount), 0))
            .filter(TransferRecord.source_account == account.name)
            .scalar() or 0
        )
        expense_spend = (
            db.query(func.coalesce(func.sum(ExpenseRecord.amount), 0))
            .filter(ExpenseRecord.payment_source == account.name)
            .scalar() or 0
        )
        lent_out = (
            db.query(func.coalesce(func.sum(LendingRecord.amount), 0))
            .filter(
                LendingRecord.account == account.name,
                LendingRecord.direction == LendingDirection.LENT,
            )
            .scalar() or 0
        )
        borrowed_in = (
            db.query(func.coalesce(func.sum(LendingRecord.amount), 0))
            .filter(
                LendingRecord.account == account.name,
                LendingRecord.direction == LendingDirection.BORROWED,
            )
            .scalar() or 0
        )
        income_in = (
            db.query(func.coalesce(func.sum(IncomeRecord.amount), 0))
            .filter(IncomeRecord.deposit_account == account.name)
            .scalar() or 0
        )

        balance += incoming_transfers
        balance -= outgoing_transfers
        balance -= expense_spend
        balance -= lent_out
        balance += borrowed_in
        balance += income_in

        account.current_balance = balance
