from sqlalchemy.orm import joinedload

from db.models import BaseRecord, LendingRecord
from models.selectors import RecordSelector, TargetRecord


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
        # future filters go here
        status = filters.get("status")
        if status:
            pass

        time_period = filters.get("time_period")
        if time_period:
            pass

    return query.order_by(BaseRecord.created_at.desc()).all()
