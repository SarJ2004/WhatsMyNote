from calendar import monthrange
from datetime import date, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from db.schema import BaseRecord, TransferRecord
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


def resolve_record(db, selector: RecordSelector):
    query = (
        db.query(TransferRecord)
        .join(BaseRecord)
        .options(joinedload(TransferRecord.record))
    )

    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()

    if selector.target == TargetRecord.ACCOUNT and selector.account:
        return (
            query.filter(
                or_(
                    TransferRecord.source_account == selector.account,
                    TransferRecord.destination_account == selector.account,
                )
            )
            .order_by(BaseRecord.created_at.desc())
            .first()
        )

    return None


def resolve_records(
    db,
    from_accounts: list[str] | None = None,
    to_accounts: list[str] | None = None,
    filters: dict[str, str] | None = None,
):
    query = (
        db.query(TransferRecord)
        .join(BaseRecord)
        .options(joinedload(TransferRecord.record))
    )

    if from_accounts:
        query = query.filter(TransferRecord.source_account.in_(from_accounts))

    if to_accounts:
        query = query.filter(TransferRecord.destination_account.in_(to_accounts))

    if filters:
        transfer_date = filters.get("transfer_date")
        if transfer_date:
            query = query.filter(TransferRecord.transfer_date == date.fromisoformat(transfer_date))

        today = filters.get("today")
        if today:
            query = query.filter(TransferRecord.transfer_date == date.today())

        yesterday = filters.get("yesterday")
        if yesterday:
            query = query.filter(TransferRecord.transfer_date == date.today() - timedelta(days=1))

        month = filters.get("month")
        if month:
            start, end = _month_bounds(month)
            query = query.filter(TransferRecord.transfer_date.between(start, end))

        start = filters.get("from")
        end = filters.get("to")
        if start and end:
            query = query.filter(
                TransferRecord.transfer_date.between(
                    date.fromisoformat(start),
                    date.fromisoformat(end),
                )
            )

    return query.order_by(BaseRecord.created_at.desc()).all()