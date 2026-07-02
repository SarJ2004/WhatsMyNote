from calendar import monthrange
from datetime import date, datetime

from sqlalchemy.orm import joinedload

from db.schema import BaseRecord, BudgetRecord
from models.selectors import RecordSelector, TargetRecord


def _month_bounds(value: str):
    if value.lower() in {"current", "this"}:
        today = date.today()
        return today.replace(day=1), today.replace(
            day=monthrange(today.year, today.month)[1]
        )
    if value.lower() == "last":
        today = date.today()
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
        return date(year, month, 1), date(year, month, monthrange(year, month)[1])
    parsed = datetime.strptime(value, "%B %Y").date()
    return parsed.replace(day=1), parsed.replace(
        day=monthrange(parsed.year, parsed.month)[1]
    )


def resolve_record(db, selector: RecordSelector):
    query = (
        db.query(BudgetRecord).join(BaseRecord).options(joinedload(BudgetRecord.record))
    )
    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()
    if selector.target == TargetRecord.CATEGORY and selector.category:
        return (
            query.filter(BudgetRecord.category == selector.category)
            .order_by(BaseRecord.created_at.desc())
            .first()
        )
    return None


def resolve_records(
    db, categories: list[str] | None = None, filters: dict[str, str] | None = None
):
    query = (
        db.query(BudgetRecord).join(BaseRecord).options(joinedload(BudgetRecord.record))
    )
    if categories:
        query = query.filter(BudgetRecord.category.in_(categories))
    if filters:
        month = filters.get("month")
        if month:
            start, end = _month_bounds(month)
            query = query.filter(BudgetRecord.budget_date.between(start, end))
    return query.order_by(BaseRecord.created_at.desc()).all()
