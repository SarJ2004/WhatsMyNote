from db.models import LendingRecord
from models.selectors import RecordSelector, TargetRecord


def resolve_record(db, selector: RecordSelector):
    """
    Resolve a selector into a single LendingRecord.

    LAST:
        Most recent record overall.

    PERSON:
        Most recent record for that person.
    """

    if selector.target == TargetRecord.LAST:
        return db.query(LendingRecord).order_by(LendingRecord.created_at.desc()).first()

    if selector.target == TargetRecord.PERSON:
        return (
            db.query(LendingRecord)
            .filter(LendingRecord.person == selector.person)
            .order_by(LendingRecord.created_at.desc())
            .first()
        )

    return None


def resolve_records(
    db, people: list[str] | None = None, filters: dict[str, str] | None = None
):
    """
    Resolve query filters into multiple LendingRecords.
    Used by query execution.
    """

    query = db.query(LendingRecord)
    if people:
        query = query.filter(LendingRecord.person.in_(people))
    if filters:
        # future filters go here
        # status, date ranges, etc.
        status = filters.get("status")
        if status:
            ...
            pass
        time_period = filters.get("time_period")
        if time_period:
            ...
            pass
    return query.order_by(LendingRecord.created_at.desc()).all()
