"""Budget alert system — checks spending against budget limits."""

from __future__ import annotations

from calendar import monthrange
from datetime import date

from sqlalchemy import func

from db.schema import BaseRecord, BudgetRecord, ExpenseRecord
from records.normalization import normalize_label

ALERT_LEVELS = [0.25, 0.5, 0.75, 1.0]


def _month_bounds(anchor_date: date) -> tuple[date, date]:
    start = anchor_date.replace(day=1)
    end = anchor_date.replace(day=monthrange(anchor_date.year, anchor_date.month)[1])
    return start, end


def _budget_label(category: str) -> str:
    return normalize_label(category or "") or "Overall"


def _current_month_total(
    db, *, category: str | None = None, anchor_date: date | None = None
) -> int:
    anchor = anchor_date or date.today()
    start, end = _month_bounds(anchor)

    query = db.query(func.coalesce(func.sum(ExpenseRecord.amount), 0)).join(BaseRecord)
    query = query.filter(ExpenseRecord.expense_date.between(start, end))

    if category and category != "Overall":
        query = query.filter(ExpenseRecord.category == category)

    return int(query.scalar() or 0)


def _latest_budget_for_label(db, label: str):
    return (
        db.query(BudgetRecord)
        .join(BaseRecord)
        .filter(BudgetRecord.category == label)
        .order_by(BaseRecord.created_at.desc())
        .first()
    )


def _threshold_message(label: str, spent: int, limit: int) -> str | None:
    if limit <= 0:
        return None

    ratio = spent / limit
    if ratio < ALERT_LEVELS[0]:
        return None

    if ratio >= 1:
        return f"Budget exceeded for {label}: {spent}/{limit}."

    crossed = max(level for level in ALERT_LEVELS if ratio >= level)
    percent = int(crossed * 100)
    return f"Budget alert for {label}: {percent}% used ({spent}/{limit})."


def build_budget_alerts_for_budget(db, budget_record) -> list[str]:
    label = _budget_label(budget_record.category)
    spent = _current_month_total(
        db,
        category=None if label == "Overall" else label,
        anchor_date=budget_record.budget_date or date.today(),
    )
    message = _threshold_message(label, spent, budget_record.amount)
    return [message] if message else []


def build_budget_alerts_for_expense(db, expense_record) -> list[str]:
    alerts: list[str] = []
    anchor = expense_record.expense_date or date.today()

    overall_budget = _latest_budget_for_label(db, "Overall")
    if overall_budget is not None:
        spent = _current_month_total(db, anchor_date=anchor)
        message = _threshold_message("Overall", spent, overall_budget.amount)
        if message:
            alerts.append(message)

    if expense_record.category:
        category_budget = _latest_budget_for_label(db, expense_record.category)
        if category_budget is not None:
            spent = _current_month_total(
                db, category=expense_record.category, anchor_date=anchor
            )
            message = _threshold_message(
                expense_record.category, spent, category_budget.amount
            )
            if message:
                alerts.append(message)

    return alerts
