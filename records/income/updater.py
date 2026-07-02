from db.config import SessionLocal
from records.income.models import UpdateIncome, UpdateOperation
from records.income.resolver import resolve_record


def record_updater(state):
    extraction: UpdateIncome = state.extraction
    db = SessionLocal()

    try:
        record = resolve_record(db, extraction.selector)

        if record is None:
            return {"error": "No matching record found."}

        for update in extraction.updates:
            field = update.field.value

            if not hasattr(record, field):
                return {"error": f"Field '{field}' cannot be updated."}

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
            "response": f"Updated income from {record.source}.",
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()