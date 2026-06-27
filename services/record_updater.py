from models.update_record_model import (
    UpdateRecord,
    UpdateOperation,
)
from db.config import SessionLocal
from services.record_resolver import resolve_record


def record_updater(state):
    extraction: UpdateRecord = state.extraction

    db = SessionLocal()

    try:
        record = resolve_record(
            db,
            extraction.selector,
        )

        if record is None:
            return {"error": "No matching record found."}

        for update in extraction.updates:
            field = update.field
            if not hasattr(record, field):
                return {"error": f"Field '{field}' can not be updated"}
            current_value = getattr(record, field)

            match update.operation:
                case UpdateOperation.SET:
                    setattr(record, field, update.value)

                case UpdateOperation.ADD:
                    setattr(record, field, current_value + update.value)

                case UpdateOperation.SUB:
                    setattr(record, field, current_value - update.value)

                case UpdateOperation.MULTIPLY:
                    setattr(record, field, current_value * update.value)

        db.commit()

        db.refresh(record)

        return {
            "updated_record_id": record.record_id,
            "response": f"Updated record for: {record.person}",
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
