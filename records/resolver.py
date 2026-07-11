"""Unified record resolver — resolves a RecordSelector to a DB record for any type."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
import re

from sqlalchemy.orm import joinedload

from db.schema import (
    BaseRecord, ExpenseRecord, IncomeRecord, LendingRecord,
    TransferRecord, AccountRecord, BudgetRecord,
)
from records.models.common import RecordSelector, TargetRecord
from records.normalization import normalize_label, normalize_label_list


# ── Date helpers ───────────────────────────────────────────────

def _month_bounds(value: str, fallback_year: int | None = None):
    if value.lower() in {"current", "this"}:
        today = date.today()
        start = today.replace(day=1)
        end_day = monthrange(today.year, today.month)[1]
        return start, today.replace(day=end_day)
    if value.lower() == "last":
        today = date.today()
        year = today.year if today.month > 1 else today.year - 1
        month = today.month - 1 if today.month > 1 else 12
        start = date(year, month, 1)
        end_day = monthrange(year, month)[1]
        return start, date(year, month, end_day)
    iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})", value)
    if iso_match:
        year, month = int(iso_match.group(1)), int(iso_match.group(2))
        start = date(year, month, 1)
        end_day = monthrange(year, month)[1]
        return start, date(year, month, end_day)
    parsed = datetime.strptime(value, "%B %Y").date()
    start = parsed.replace(day=1)
    end_day = monthrange(parsed.year, parsed.month)[1]
    return start, parsed.replace(day=end_day)


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


# ── ORM model mapping ─────────────────────────────────────────

_TYPE_TO_ORM = {
    "expense": ExpenseRecord,
    "income": IncomeRecord,
    "lending": LendingRecord,
    "transfer": TransferRecord,
    "account": AccountRecord,
    "budget": BudgetRecord,
}

_DATE_FIELD = {
    "expense": "expense_date",
    "income": "income_date",
    "transfer": "transfer_date",
    "lending": "expected_payback_by",
    "budget": "budget_date",
}


# ── Single-record resolver ────────────────────────────────────

def resolve_record(db, record_type: str, selector: RecordSelector):
    """Resolve a selector to a single ORM record."""
    orm_cls = _TYPE_TO_ORM.get(record_type)
    if orm_cls is None:
        return None

    query = (
        db.query(orm_cls)
        .join(BaseRecord)
        .options(joinedload(orm_cls.record))
    )

    if selector.target == TargetRecord.ID and selector.record_id:
        return query.filter(orm_cls.record_id == selector.record_id).first()

    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()

    if selector.target == TargetRecord.PERSON and selector.person:
        if hasattr(orm_cls, "person"):
            person = normalize_label(selector.person)
            return (
                query.filter(orm_cls.person == person)
                .order_by(BaseRecord.created_at.desc())
                .first()
            )

    if selector.target == TargetRecord.CATEGORY and selector.category:
        if hasattr(orm_cls, "category"):
            category = normalize_label(selector.category)
            return (
                query.filter(orm_cls.category == category)
                .order_by(BaseRecord.created_at.desc())
                .first()
            )

    if selector.target == TargetRecord.ACCOUNT and selector.account:
        account = normalize_label(selector.account)
        if hasattr(orm_cls, "name"):
            return query.filter(orm_cls.name == account).first()
        if hasattr(orm_cls, "source_account"):
            return (
                query.filter(orm_cls.source_account == account)
                .order_by(BaseRecord.created_at.desc())
                .first()
            )
        if hasattr(orm_cls, "account"):
            return (
                query.filter(orm_cls.account == account)
                .order_by(BaseRecord.created_at.desc())
                .first()
            )

    if selector.target == TargetRecord.SOURCE and selector.source:
        source = normalize_label(selector.source)
        if hasattr(orm_cls, "source"):
            return (
                query.filter(orm_cls.source == source)
                .order_by(BaseRecord.created_at.desc())
                .first()
            )

    return None


def resolve_records_for_selector(db, record_type: str, selector: RecordSelector):
    """Resolve a selector to a list of matching ORM records."""
    orm_cls = _TYPE_TO_ORM.get(record_type)
    if orm_cls is None:
        return []

    query = (
        db.query(orm_cls)
        .join(BaseRecord)
        .options(joinedload(orm_cls.record))
    )

    if selector.target == TargetRecord.ID and selector.record_id:
        rec = query.filter(orm_cls.record_id == selector.record_id).first()
        return [rec] if rec else []

    if selector.target == TargetRecord.LAST:
        rec = query.order_by(BaseRecord.created_at.desc()).first()
        return [rec] if rec else []

    if selector.target == TargetRecord.PERSON and selector.person:
        if hasattr(orm_cls, "person"):
            person = normalize_label(selector.person)
            return (
                query.filter(orm_cls.person == person)
                .order_by(BaseRecord.created_at.desc())
                .all()
            )

    if selector.target == TargetRecord.CATEGORY and selector.category:
        if hasattr(orm_cls, "category"):
            category = normalize_label(selector.category)
            return (
                query.filter(orm_cls.category == category)
                .order_by(BaseRecord.created_at.desc())
                .all()
            )

    if selector.target == TargetRecord.ACCOUNT and selector.account:
        account = normalize_label(selector.account)
        if hasattr(orm_cls, "name"):
            return query.filter(orm_cls.name == account).all()
        if hasattr(orm_cls, "source_account"):
            return (
                query.filter(orm_cls.source_account == account)
                .order_by(BaseRecord.created_at.desc())
                .all()
            )
        if hasattr(orm_cls, "account"):
            return (
                query.filter(orm_cls.account == account)
                .order_by(BaseRecord.created_at.desc())
                .all()
            )

    if selector.target == TargetRecord.SOURCE and selector.source:
        source = normalize_label(selector.source)
        if hasattr(orm_cls, "source"):
            return (
                query.filter(orm_cls.source == source)
                .order_by(BaseRecord.created_at.desc())
                .all()
            )

    return []


# ── Multi-record resolver (for queries) ───────────────────────

def resolve_records(db, record_type: str, filters: dict | None = None, **kwargs):
    """Resolve query filters into multiple ORM records."""
    orm_cls = _TYPE_TO_ORM.get(record_type)
    if orm_cls is None:
        return []

    query = (
        db.query(orm_cls)
        .join(BaseRecord)
        .options(joinedload(orm_cls.record))
    )

    # Apply keyword-based column filters
    for key, values in kwargs.items():
        if not values:
            continue
        values = normalize_label_list(values) if isinstance(values, list) else values
        if hasattr(orm_cls, key):
            col = getattr(orm_cls, key)
            if isinstance(values, list):
                query = query.filter(col.in_(values))
            else:
                query = query.filter(col == values)

    # Apply date/time filters
    if filters:
        date_col_name = _DATE_FIELD.get(record_type)
        if date_col_name and hasattr(orm_cls, date_col_name):
            date_col = getattr(orm_cls, date_col_name)

            if filters.get("today"):
                query = query.filter(date_col == date.today())
            if filters.get("yesterday"):
                query = query.filter(date_col == date.today() - timedelta(days=1))
            if filters.get("week"):
                start, end = _week_bounds(filters["week"])
                query = query.filter(date_col.between(start, end))
            if filters.get("month"):
                start, end = _month_bounds(filters["month"])
                query = query.filter(date_col.between(start, end))
            if filters.get("year"):
                start, end = _year_bounds(filters["year"])
                query = query.filter(date_col.between(start, end))
            if filters.get("from") and filters.get("to"):
                query = query.filter(
                    date_col.between(
                        date.fromisoformat(filters["from"]),
                        date.fromisoformat(filters["to"]),
                    )
                )
            if filters.get("date"):
                val = filters["date"]
                iso_month = re.fullmatch(r"(\d{4})-(\d{1,2})", val)
                if iso_month:
                    start, end = _month_bounds(val)
                    query = query.filter(date_col.between(start, end))
                else:
                    query = query.filter(date_col == date.fromisoformat(val))
            if filters.get("expense_date"):
                query = query.filter(
                    date_col == date.fromisoformat(filters["expense_date"])
                )

    return query.order_by(BaseRecord.created_at.desc()).all()
