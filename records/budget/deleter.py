from db.config import SessionLocal
from records.budget.models import DeleteBudget
from records.budget.resolver import resolve_record


def record_deleter(state):
    extraction: DeleteBudget = state.extraction
    db = SessionLocal()
    try:
        record = resolve_record(db, extraction.selector)
        if record is None:
            return {"error": "No matching budget found."}
        record_id = record.record_id
        category = record.category
        db.delete(record.record)
        db.commit()
        return {
            "response": f"Deleted budget: {category}",
            "deleted_record_id": record_id,
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
