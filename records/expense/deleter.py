from records.expense.models import DeleteExpense
from db.config import SessionLocal
from records.expense.resolver import resolve_record


def record_deleter(state):
    extraction: DeleteExpense = state.extraction
    db = SessionLocal()

    try:
        record = resolve_record(
            db,
            extraction.selector,
        )

        if record is None:
            return {"error": "No matching record found."}

        amount = record.amount
        category = record.category
        merchant = record.merchant
        record_id = record.record_id

        # Delete the parent record (cascade deletes ExpenseRecord)
        db.delete(record.record)

        db.commit()

        description = merchant or category or "Expense"

        return {
            "response": f"Deleted expense: {description} ({amount})",
            "deleted_record_id": record_id,
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    finally:
        db.close()
