from db.config import SessionLocal
from db.schema import BaseRecord, TransferRecord, RecordType


def record_saver(state):
    session = SessionLocal()
    saved_ids = []

    try:
        for record in state.extraction.records:
            base_record = BaseRecord(
                record_type=RecordType.TRANSFER,
                raw_text=state.raw_text,
            )

            base_record.transfer = TransferRecord(
                source_account=record.source_account,
                destination_account=record.destination_account,
                amount=record.amount,
                transfer_date=record.transfer_date,
                notes=record.notes,
            )

            session.add(base_record)
            session.flush()

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
