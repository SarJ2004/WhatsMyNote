"""Generic record deleter — handles delete for all record types."""

from __future__ import annotations

from db.config import SessionLocal
from records.account_utils import sync_account_balances
from records.models.common import RecordSelector
from records.resolver import resolve_record


def record_deleter(state):
    """Generic deleter node — resolves and deletes a record based on state."""
    extraction = state.get("extraction")
    record_type = state.get("record_type")

    if not extraction or not record_type:
        return {"error": "Missing extraction or record type."}

    # If HITL selected specific records, override the selector
    target_ids = None
    if state.get("selected_record_ids"):
        target_ids = state.get("selected_record_ids")
    elif state.get("selected_record_id"):
        target_ids = [state.get("selected_record_id")]

    selector_data = extraction.get("selector")
    selector = None
    if target_ids is None:
        if not selector_data:
            return {"error": "No selector provided for deletion."}
        try:
            selector = RecordSelector.model_validate(selector_data)
        except Exception as e:
            return {"error": f"Invalid selector: {e}"}

    db = SessionLocal()

    try:
        if target_ids:
            from records.models.common import TargetRecord
            deleted = []
            for rid in target_ids:
                sel = RecordSelector(target=TargetRecord.ID, record_id=rid)
                record = resolve_record(db, record_type, sel)
                if record:
                    deleted.append(record.record_id)
                    db.delete(record.record)
            
            if not deleted:
                return {"error": "No matching records found for the selected IDs."}
                
            sync_account_balances(db)
            db.commit()
            return {"deleted_record_ids": deleted}
            
        else:
            record = resolve_record(db, record_type, selector)

            if record is None:
                return {"error": "No matching record found."}

            record_id = record.record_id

            # Delete the parent record (cascade deletes the type-specific record)
            db.delete(record.record)
            sync_account_balances(db)
            db.commit()

            return {"deleted_record_id": record_id}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
