from db.config import SessionLocal
from db.schema import BaseRecord, BudgetRecord, RecordType


def record_saver(state):
    session = SessionLocal()
    saved_ids = []

    try:
        for record in state.extraction.records:
            base_record = BaseRecord(record_type=RecordType.BUDGET, raw_text=state.raw_text)
            base_record.budget = BudgetRecord(
                category=record.category,
                amount=record.amount,
                period=record.period,
                budget_date=record.budget_date,
                notes=record.notes,
            )
            session.add(base_record)
            session.flush()
            saved_ids.append(base_record.id)
        session.commit()
    except Exception as e:
        session.rollback()
        return {"error": f"Failed to save budget records.\n{str(e)}"}
    finally:
        session.close()
    return {"saved_record_ids": saved_ids, "response": f"Saved {len(saved_ids)} budget record(s)."}
