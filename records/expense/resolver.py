from sqlalchemy.orm import joinedload

from db.schema import BaseRecord, ExpenseRecord
from models.selectors import RecordSelector, TargetRecord


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
            # TODO
            pass

        today = filters.get("today")
        if today:
            # TODO
            pass

        yesterday = filters.get("yesterday")
        if yesterday:
            # TODO
            pass

        week = filters.get("week")
        if week:
            # TODO
            pass

        month = filters.get("month")
        if month:
            # TODO
            pass

        year = filters.get("year")
        if year:
            # TODO
            pass

        start = filters.get("from")
        end = filters.get("to")
        if start and end:
            # TODO
            pass

    return query.order_by(BaseRecord.created_at.desc()).all()
