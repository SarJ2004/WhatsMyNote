from datetime import date, datetime, timedelta
from calendar import monthrange

from sqlalchemy.orm import joinedload

from db.schema import BaseRecord, IncomeRecord
from models.selectors import RecordSelector, TargetRecord


def _month_bounds(value: str):
    if value.lower() in {"current", "this"}:
        today = date.today()
        start = today.replace(day=1)
        end = today.replace(day=monthrange(today.year, today.month)[1])
        return start, end

    if value.lower() == "last":
        today = date.today()
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        return start, end

    parsed = datetime.strptime(value, "%B %Y").date()
    start = parsed.replace(day=1)
    end = parsed.replace(day=monthrange(parsed.year, parsed.month)[1])
    return start, end


def _year_bounds(value: str):
    if value.lower() in {"current", "this"}:
        year = date.today().year
    elif value.lower() == "last":
        year = date.today().year - 1
    else:
        year = int(value)
    return date(year, 1, 1), date(year, 12, 31)


def resolve_record(db, selector: RecordSelector):
    query = (
        db.query(IncomeRecord)
        .join(BaseRecord)
        .options(joinedload(IncomeRecord.record))
    )

    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()

    if selector.target == TargetRecord.SOURCE and selector.source:
        return (
            query.filter(IncomeRecord.source == selector.source)
            .order_by(BaseRecord.created_at.desc())
            .first()
        )

    return None


def resolve_records(
    db,
    sources: list[str] | None = None,
    filters: dict[str, str] | None = None,
):
    query = (
        db.query(IncomeRecord)
        .join(BaseRecord)
        .options(joinedload(IncomeRecord.record))
    )

    if sources:
        query = query.filter(IncomeRecord.source.in_(sources))

    if filters:
        income_date = filters.get("income_date")
        if income_date:
            query = query.filter(IncomeRecord.income_date == date.fromisoformat(income_date))

        today = filters.get("today")
        if today:
            query = query.filter(IncomeRecord.income_date == date.today())

        yesterday = filters.get("yesterday")
        if yesterday:
            query = query.filter(IncomeRecord.income_date == date.today() - timedelta(days=1))

        month = filters.get("month")
        if month:
            start, end = _month_bounds(month)
            query = query.filter(IncomeRecord.income_date.between(start, end))

        year = filters.get("year")
        if year:
            start, end = _year_bounds(year)
            query = query.filter(IncomeRecord.income_date.between(start, end))

        start = filters.get("from")
        end = filters.get("to")
        if start and end:
            query = query.filter(
                IncomeRecord.income_date.between(
                    date.fromisoformat(start),
                    date.fromisoformat(end),
                )
            )

    return query.order_by(BaseRecord.created_at.desc()).all()