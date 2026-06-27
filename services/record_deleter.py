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
        record_id = record.record_id

        # Delete the parent record.
        db.delete(record.record)

        db.commit()

        return {
            "response": f"Deleted record: {person} ({amount})",
            "deleted_record_id": record_id,
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
