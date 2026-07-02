from db.config import SessionLocal
from db.schema import BaseRecord


def delete_last_record(state):
    db = SessionLocal()

    try:
        record = db.query(BaseRecord).order_by(BaseRecord.created_at.desc()).first()

        if record is None:
            return {"error": "No records found to delete."}

        record_id = record.id
        record_type = record.record_type.value

        db.delete(record)
        db.commit()

        return {
            "deleted_record_id": record_id,
            "response": f"Deleted last record ({record_type}) #{record_id}",
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
