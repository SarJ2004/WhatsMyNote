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

            current_value = getattr(
                record,
                field,
            )

            if update.operation == UpdateOperation.SET:
                setattr(
                    record,
                    field,
                    update.value,
                )

            elif update.operation == UpdateOperation.ADD:
                setattr(
                    record,
                    field,
                    current_value + update.value,
                )

            elif update.operation == UpdateOperation.SUB:
                setattr(
                    record,
                    field,
                    current_value - update.value,
                )

            elif update.operation == UpdateOperation.MULTIPLY:
                setattr(
                    record,
                    field,
                    current_value * update.value,
                )

        db.commit()
        db.refresh(record)

        return {
            "updated_record_id": record.id,
            "response": f"Updated record for: {record.person}",
        }
    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
