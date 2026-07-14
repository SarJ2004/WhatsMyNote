"""Generic record updater — handles update for all record types."""

from __future__ import annotations

from backend.db.config import SessionLocal
from backend.records.account_utils import sync_account_balances
from backend.records.models.common import RecordSelector, UpdateOperation
from backend.records.normalization import normalize_label, normalize_currency, normalize_period
from backend.records.resolver import resolve_record

NORMALIZED_FIELDS = {
    "category", "merchant", "payment_source", "item", 
    "source", "deposit_account", "person", "account", 
    "source_account", "destination_account", "name"
}


def record_updater(state):
    """Generic updater node — resolves and updates a record based on state."""
    extraction = state.get("extraction")
    record_type = state.get("record_type")

    if not extraction or not record_type:
        return {"error": "Missing extraction or record type."}

    # If HITL selected a specific record, override the selector
    target_id = state.get("selected_record_id")

    selector_data = extraction.get("selector")
    selector = None
    if target_id is None:
        if not selector_data:
            return {"error": "No selector provided for update."}
        try:
            selector = RecordSelector.model_validate(selector_data)
        except Exception as e:
            return {"error": f"Invalid selector: {e}"}

    if target_id:
        from backend.records.models.common import TargetRecord
        selector = RecordSelector(target=TargetRecord.ID, record_id=target_id)

    updates = extraction.get("updates", [])
    if not updates:
        return {"error": "No updates specified."}

    db = SessionLocal()

    try:
        record = resolve_record(db, record_type, selector)

        if record is None:
            return {"error": "No matching record found."}

        for update in updates:
            field = update.get("field") if isinstance(update, dict) else update.field
            operation = update.get("operation", "set") if isinstance(update, dict) else update.operation
            value = update.get("value") if isinstance(update, dict) else update.value

            if not hasattr(record, field):
                return {"error": f"Field '{field}' cannot be updated."}

            current_value = getattr(record, field)

            match operation:
                case "set" | UpdateOperation.SET:
                    if field in NORMALIZED_FIELDS and isinstance(value, str):
                        value = normalize_label(value)
                    elif field == "currency" and isinstance(value, str):
                        value = normalize_currency(value)
                    elif field == "period" and isinstance(value, str):
                        value = normalize_period(value)
                        
                    setattr(record, field, value)
                case "add" | UpdateOperation.ADD:
                    setattr(record, field, current_value + value)
                case "subtract" | UpdateOperation.SUB:
                    setattr(record, field, current_value - value)
                case "multiply" | UpdateOperation.MULTIPLY:
                    setattr(record, field, current_value * value)

        db.flush()
        db.refresh(record)
        sync_account_balances(db)
        db.commit()

        return {
            "updated_record_id": record.record_id,
            "selected_record_id": None,
            "selected_record_ids": None
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()
