from datetime import date, datetime, timedelta, time, timezone
from calendar import monthrange

from sqlalchemy.orm import joinedload

from db.schema import BaseRecord, LendingRecord
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

    parsed = date.strptime(value, "%B %Y")
    start = parsed.replace(day=1)
    end = parsed.replace(day=monthrange(parsed.year, parsed.month)[1])
    return start, end


def _week_bounds(value: str):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    if value.lower() in {"current", "this"}:
        start = start_of_week
    else:
        start = start_of_week - timedelta(days=7)
    return start, start + timedelta(days=6)


def _created_at_range(start_date: date, end_date: date):
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    return start, end


def resolve_record(db, selector: RecordSelector):
    """
    Resolve a selector into a single LendingRecord.

    LAST:
        Most recent lending record overall.

    PERSON:
        Most recent lending record for that person.
    """

    query = (
        db.query(LendingRecord)
        .join(BaseRecord)
        .options(joinedload(LendingRecord.record))
    )

    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()

    if selector.target == TargetRecord.PERSON:
        return (
            query.filter(LendingRecord.person == selector.person)
            .order_by(BaseRecord.created_at.desc())
            .first()
        )

    return None


def resolve_records(
    db,
    people: list[str] | None = None,
    filters: dict[str, str] | None = None,
):
    """
    Resolve query filters into multiple LendingRecords.
    Used by query execution.
    """

    query = (
        db.query(LendingRecord)
        .join(BaseRecord)
        .options(joinedload(LendingRecord.record))
    )

    if people:
        query = query.filter(LendingRecord.person.in_(people))

    if filters:
        status = filters.get("status")
        if status:
            normalized = status.lower()
            if normalized == "pending":
                query = query.filter(BaseRecord.settled_at.is_(None))
            elif normalized == "paid":
                query = query.filter(BaseRecord.settled_at.is_not(None))

        time_period = filters.get("time_period")
        if time_period:
            start, end = _month_bounds(time_period)
            start_dt, end_dt = _created_at_range(start, end)
            query = query.filter(BaseRecord.created_at.between(start_dt, end_dt))

        today = filters.get("today")
        if today:
            start_dt, end_dt = _created_at_range(date.today(), date.today())
            query = query.filter(BaseRecord.created_at.between(start_dt, end_dt))

        yesterday = filters.get("yesterday")
        if yesterday:
            day = date.today() - timedelta(days=1)
            start_dt, end_dt = _created_at_range(day, day)
            query = query.filter(BaseRecord.created_at.between(start_dt, end_dt))

        week = filters.get("week")
        if week:
            start, end = _week_bounds(week)
            start_dt, end_dt = _created_at_range(start, end)
            query = query.filter(BaseRecord.created_at.between(start_dt, end_dt))

        month = filters.get("month")
        if month:
            start, end = _month_bounds(month)
            start_dt, end_dt = _created_at_range(start, end)
            query = query.filter(BaseRecord.created_at.between(start_dt, end_dt))

        year = filters.get("year")
        if year:
            if year.lower() in {"current", "this"}:
                year_value = date.today().year
            elif year.lower() == "last":
                year_value = date.today().year - 1
            else:
                year_value = int(year)
            start_dt = datetime.combine(date(year_value, 1, 1), time.min, tzinfo=timezone.utc)
            end_dt = datetime.combine(date(year_value, 12, 31), time.max, tzinfo=timezone.utc)
            query = query.filter(
                BaseRecord.created_at.between(start_dt, end_dt)
            )

    return query.order_by(BaseRecord.created_at.desc()).all()
