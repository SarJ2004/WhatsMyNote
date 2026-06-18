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
