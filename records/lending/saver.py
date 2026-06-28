from db.config import SessionLocal
from db.schema import BaseRecord, LendingRecord, RecordType, LendingDirection


def record_saver(state):
    session = SessionLocal()
    saved_ids = []

    try:
        for record in state.extraction.records:
            # Create the base record
            base_record = BaseRecord(
                record_type=RecordType.LENDING,
                raw_text=state.raw_text,
            )

            # Create the lending record
            base_record.lending = LendingRecord(
                person=record.person,
                amount=record.amount,
                direction=record.direction,
                expected_payback_by=record.expected_payback_by,
            )
            session.add(base_record)
            session.flush()  # Flush to get the ID of the base_record

            saved_ids.append(base_record.id)

        session.commit()

    except Exception as e:
        session.rollback()
        return {"error": f"Failed to save records.\n{str(e)}"}

    finally:
        session.close()

    return {
        "saved_record_ids": saved_ids,
        "response": f"Saved {len(saved_ids)} record(s).",
    }
