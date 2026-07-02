from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from db.schema import AccountRecord, BaseRecord, TransferRecord
from models.selectors import RecordSelector, TargetRecord


def _current_balance(db, account_name: str):
    account = db.query(AccountRecord).join(BaseRecord).filter(AccountRecord.name == account_name).first()
    if account is None:
        return None

    incoming = (
        db.query(func.coalesce(func.sum(TransferRecord.amount), 0))
        .filter(TransferRecord.destination_account == account_name)
        .scalar()
        or 0
    )
    outgoing = (
        db.query(func.coalesce(func.sum(TransferRecord.amount), 0))
        .filter(TransferRecord.source_account == account_name)
        .scalar()
        or 0
    )
    return account.opening_balance + incoming - outgoing


def resolve_record(db, selector: RecordSelector):
    query = db.query(AccountRecord).join(BaseRecord).options(joinedload(AccountRecord.record))

    if selector.target == TargetRecord.LAST:
        return query.order_by(BaseRecord.created_at.desc()).first()

    if selector.target == TargetRecord.ACCOUNT and selector.account:
        return query.filter(AccountRecord.name == selector.account).first()

    return None


def resolve_records(db, accounts: list[str] | None = None, filters: dict[str, str] | None = None):
    query = db.query(AccountRecord).join(BaseRecord).options(joinedload(AccountRecord.record))

    if accounts:
        query = query.filter(AccountRecord.name.in_(accounts))

    if filters and filters.get("currency"):
        query = query.filter(AccountRecord.currency == filters["currency"])

    return query.order_by(BaseRecord.created_at.desc()).all()


def current_balance(db, account_name: str):
    return _current_balance(db, account_name)
