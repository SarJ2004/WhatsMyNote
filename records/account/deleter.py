from db.config import SessionLocal
from records.account.models import DeleteAccount
from records.account.resolver import resolve_record


def record_deleter(state):
    extraction: DeleteAccount = state.extraction
    db = SessionLocal()

    try:
        record = resolve_record(db, extraction.selector)
        if record is None:
            return {"error": "No matching account found."}

        record_id = record.record_id
        name = record.name

        db.delete(record.record)
        db.commit()

        return {"response": f"Deleted account: {name}", "deleted_record_id": record_id}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
