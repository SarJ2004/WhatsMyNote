from db.config import SessionLocal
from records.income.models import DeleteIncome
from records.income.resolver import resolve_record


def record_deleter(state):
    extraction: DeleteIncome = state.extraction
    db = SessionLocal()

    try:
        record = resolve_record(db, extraction.selector)

        if record is None:
            return {"error": "No matching record found."}

        record_id = record.record_id
        source = record.source
        amount = record.amount

        db.delete(record.record)
        db.commit()

        return {
            "response": f"Deleted income: {source} ({amount})",
            "deleted_record_id": record_id,
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()