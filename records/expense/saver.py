from db.config import SessionLocal
from db.schema import BaseRecord, ExpenseRecord, RecordType


def record_saver(state):
    session = SessionLocal()
    saved_ids = []

    try:
        for record in state.extraction.records:
            # Create the base record
            base_record = BaseRecord(
                record_type=RecordType.EXPENSE,
                raw_text=state.raw_text,
            )

            # Create the expense record
            base_record.expense = ExpenseRecord(
                amount=record.amount,
                category=record.category,
                merchant=record.merchant,
                payment_source=record.payment_source,
                expense_date=record.expense_date,
                notes=record.notes,
            )

            session.add(base_record)
            session.flush()  # Flush to get the ID of the base record

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
