from db.config import SessionLocal
from records.transfer.models import DeleteTransfer
from records.transfer.resolver import resolve_record


def record_deleter(state):
    extraction: DeleteTransfer = state.extraction
    db = SessionLocal()

    try:
        record = resolve_record(db, extraction.selector)

        if record is None:
            return {"error": "No matching record found."}

        record_id = record.record_id
        source_account = record.source_account
        destination_account = record.destination_account
        amount = record.amount

        db.delete(record.record)
        db.commit()

        return {
            "response": f"Deleted transfer: {source_account} -> {destination_account} ({amount})",
            "deleted_record_id": record_id,
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()