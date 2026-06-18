from models.delete_record_model import DeleteRecord
from db.config import SessionLocal
from services.record_resolver import resolve_record


def record_deleter(state):
    extraction: DeleteRecord = state.extraction
    db = SessionLocal()

    try:
        record = resolve_record(
            db,
            extraction.selector,
        )

        if record is None:
            return {"error": "No matching record found."}

        person = record.person
        amount = record.amount

        db.delete(record)
        db.commit()

        return {
            "response": f"Deleted record: {person} ({amount})",
            "deleted_record_id": record.id,
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
