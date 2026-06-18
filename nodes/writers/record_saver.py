from db.config import SessionLocal
from db.models import LendingRecord


def record_saver(state):
    session = SessionLocal()
    saved_ids = []
    try:
        db_records = []
        for record in state.extraction.records:
            db_record = LendingRecord(
                person=record.person,
                amount=record.amount,
                direction=record.direction,
                expected_payback_by=record.expected_payback_by,
                raw_text=state.raw_text,
            )
            session.add(db_record)
            db_records.append(db_record)

        session.commit()
        saved_ids = [r.id for r in db_records]
    except Exception as e:
        session.rollback()
        return {"error": f"Failed to save records.\n str{e}"}
    finally:
        session.close()
    return {
        "saved_record_ids": saved_ids,
        "response": f"Saved {len(saved_ids)} record(s).",
    }
