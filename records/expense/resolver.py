from calendar import monthrange
from datetime import date, datetime, timedelta

from sqlalchemy.orm import joinedload

from db.schema import BaseRecord, ExpenseRecord
from models.selectors import RecordSelector, TargetRecord


def _month_bounds(value: str, fallback_year: int | None = None):
    if value.lower() in {"current", "this"}:
        today = date.today()
        start = today.replace(day=1)
        end_day = monthrange(today.year, today.month)[1]
        end = today.replace(day=end_day)
        return start, end

    if value.lower() == "last":
        today = date.today()
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
        start = date(year, month, 1)
        end_day = monthrange(year, month)[1]
        end = date(year, month, end_day)
        return start, end

    parsed = datetime.strptime(value, "%B %Y").date()
    start = parsed.replace(day=1)
    end_day = monthrange(parsed.year, parsed.month)[1]
    end = parsed.replace(day=end_day)
    return start, end


def _year_bounds(value: str):
    if value.lower() in {"current", "this"}:
        year = date.today().year
    elif value.lower() == "last":
        year = date.today().year - 1
    else:
        year = int(value)
    return date(year, 1, 1), date(year, 12, 31)


def _week_bounds(value: str):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    if value.lower() in {"current", "this"}:
        start = start_of_week
    else:
        start = start_of_week - timedelta(days=7)
    return start, start + timedelta(days=6)


def resolve_record(db, selector: RecordSelector):
    """
    Resolve a selector into a single ExpenseRecord.

    LAST:
        Most recent expense record overall.
    """

    query = (
        db.query(ExpenseRecord)
        .join(BaseRecord)
        .options(joinedload(ExpenseRecord.record))
    )

    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()

    return None


def resolve_records(
    db,
    categories: list[str] | None = None,
    merchants: list[str] | None = None,
    payment_sources: list[str] | None = None,
    items: list[str] | None = None,
    filters: dict[str, str] | None = None,
):
    """
    Resolve query filters into multiple ExpenseRecords.
    Used by query execution.
    """

    query = (
        db.query(ExpenseRecord)
        .join(BaseRecord)
        .options(joinedload(ExpenseRecord.record))
    )

    # Category filter
    if categories:
        query = query.filter(ExpenseRecord.category.in_(categories))

    # Merchant filter
    if merchants:
        query = query.filter(ExpenseRecord.merchant.in_(merchants))

    # Payment source filter
    if payment_sources:
        query = query.filter(ExpenseRecord.payment_source.in_(payment_sources))
    if items:
        query = query.filter(ExpenseRecord.item.in_(items))

    # Date / time filters
    if filters:
        expense_date = filters.get("expense_date")
        if expense_date:
            query = query.filter(ExpenseRecord.expense_date == date.fromisoformat(expense_date))

        today = filters.get("today")
        if today:
            query = query.filter(ExpenseRecord.expense_date == date.today())

        yesterday = filters.get("yesterday")
        if yesterday:
            query = query.filter(ExpenseRecord.expense_date == date.today() - timedelta(days=1))

        week = filters.get("week")
        if week:
            start, end = _week_bounds(week)
            query = query.filter(ExpenseRecord.expense_date.between(start, end))

        month = filters.get("month")
        if month:
            start, end = _month_bounds(month)
            query = query.filter(ExpenseRecord.expense_date.between(start, end))

        year = filters.get("year")
        if year:
            start, end = _year_bounds(year)
            query = query.filter(ExpenseRecord.expense_date.between(start, end))

        start = filters.get("from")
        end = filters.get("to")
        if start and end:
            query = query.filter(
                ExpenseRecord.expense_date.between(
                    date.fromisoformat(start),
                    date.fromisoformat(end),
                )
            )

        single_date = filters.get("date")
        if single_date:
            query = query.filter(ExpenseRecord.expense_date == date.fromisoformat(single_date))

    return query.order_by(BaseRecord.created_at.desc()).all()
