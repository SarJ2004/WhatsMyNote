"""Simplified LangGraph orchestration — ~120 lines instead of 630."""

from langgraph.graph import START, END, StateGraph

from backend.core.state import State

from backend.agents.classifier import (
    primary_classifier,
    primary_router,
)
from backend.agents.extractor import extractor, extractor_router

from backend.records.saver import record_saver
from backend.records.updater import record_updater
from backend.records.deleter import record_deleter
from backend.records.query import query_executor

from backend.analytics.executor import analytics_query_executor


# ── Confirmation nodes ─────────────────────────────────────────

def check_confirmation(state) -> str:
    """Entry router: check if we're waiting for a confirmation response."""
    if state.get("awaiting_update_details", False):
        return "update_details_handler"
    if state.get("awaiting_confirmation", False):
        return "confirmation_handler"
    if state.get("selected_record_id") is not None or state.get("selected_record_ids") is not None:
        return "request_confirmation"
    return "primary_classifier"

def update_details_handler(state):
    """Handle raw text input for update details when the selector is already known."""
    from backend.agents.extractor import extractor
    
    # Temporarily force the intent and record_type so extractor runs correctly on the raw text
    state_copy = state.copy()
    state_copy["raw_text"] = 'Target is selected, assume selector is {"target": "id", "record_id": 0}. Extract updates: ' + state.get("raw_text", "")
    
    result = extractor(state_copy)
    
    if "error" in result:
        return {"error": result["error"], "awaiting_update_details": False}
        
    new_extraction = result.get("extraction", {})
    old_extraction = state.get("extraction", {})
    
    merged_extraction = {
        "action": "update",
        "selector": old_extraction.get("selector"),
        "updates": new_extraction.get("updates", [])
    }
    
    return {
        "extraction": merged_extraction,
        "awaiting_update_details": False
    }


def confirmation_handler(state):
    """Handle y/n confirmation responses."""
    text = state.get("raw_text", "").strip().lower()
    if text in {"y", "yes", "sure", "ok", "confirm"}:
        return {
            "awaiting_confirmation": False,
            # Clear ephemeral
            "saved_record_ids": [],
            "updated_record_id": None,
            "deleted_record_id": None,
            "deleted_record_ids": None,
            "query_result": None,
            "error": None,
            "answer": None,
            "record_preview": None,
        }
    else:
        return {
            "awaiting_confirmation": False,
            "intent": None,
            "record_type": None,
            "extraction": None,
            "saved_record_ids": [],
            "updated_record_id": None,
            "deleted_record_id": None,
            "deleted_record_ids": None,
            "query_result": None,
            "error": None,
            "answer": "Action cancelled.",
            "record_preview": None,
            "selected_record_id": None,
            "selected_record_ids": None,
        }


def confirmation_router(state) -> str:
    """Route after confirmation — execute or cancel."""
    if state.get("answer") == "Action cancelled.":
        return "response_formatter"
    if not state.get("extraction"):
        return "response_formatter"

    intent = state.get("intent")
    if intent == "delete":
        return "record_deleter"
    elif intent == "update":
        return "record_updater"
    return "response_formatter"


def request_confirmation(state):
    """Pause execution and ask user to confirm before destructive action."""
    if state.get("error"):
        return {}

    record_type = state.get("record_type", "record")
    intent = state.get("intent", "modify")
    extraction = state.get("extraction")
    
    # Try to resolve the record to show a preview
    preview_str = ""
    
    # Initialize extraction if it was None (e.g. if extractor failed and we used HITL)
    if not extraction:
        extraction = {"action": intent}
        
    if state.get("selected_record_id"):
        from backend.records.models.common import RecordSelector, TargetRecord
        selector = RecordSelector(target=TargetRecord.ID, record_id=state.get("selected_record_id"))
        extraction["selector"] = selector.model_dump()

    if extraction.get("selector"):
        from backend.db.config import SessionLocal
        from backend.records.resolver import resolve_records_for_selector
        from backend.records.models.common import RecordSelector
        from backend.records.search import _record_to_display_dict
        
        db = SessionLocal()
        try:
            selector_data = extraction.get("selector")
            selector = RecordSelector.model_validate(selector_data)
            
            # If hitl provided selections, we don't need to query for ambiguity
            if state.get("selected_record_id") or state.get("selected_record_ids"):
                if state.get("selected_record_ids"):
                    preview_str = f"\nTarget: {len(state.get('selected_record_ids'))} records selected.\n"
                else:
                    record = resolve_records_for_selector(db, record_type, selector)[0]
                    fields = {k: v for k, v in vars(record).items() if not k.startswith("_") and k != "record"}
                    preview_str = f"\nTarget: {fields}\n"
            else:
                records = resolve_records_for_selector(db, record_type, selector)
                if not records:
                    return {"error": "Could not find a matching record to modify.", "selected_record_id": None}
                
                if len(records) > 1:
                    return {
                        "search_results": [_record_to_display_dict(record_type, r) for r in records],
                        "awaiting_selection": True,
                        "answer": f"Multiple {record_type} records found. Please select which one(s) to modify."
                    }
                else:
                    record = records[0]
                    fields = {k: v for k, v in vars(record).items() if not k.startswith("_") and k != "record"}
                    preview_str = f"\nTarget: {fields}\n"
        except Exception:
            pass
        finally:
            db.close()

    if intent == "update" and not extraction.get("updates"):
        return {
            "awaiting_update_details": True,
            "extraction": extraction,
            "answer": f"What would you like to update? (e.g. 'change amount to 500' or 'set category to Food')"
        }

    # Format the updates if any exist
    updates_str = ""
    if intent == "update" and extraction.get("updates"):
        updates_list = extraction.get("updates", [])
        if updates_list:
            updates_str = "\nUpdates to apply:\n"
            for up in updates_list:
                field = up.get("field") if isinstance(up, dict) else up.field
                op = up.get("operation") if isinstance(up, dict) else up.operation
                val = up.get("value") if isinstance(up, dict) else up.value
                updates_str += f" - {field}: {op} -> {val}\n"

    return {
        "awaiting_confirmation": True,
        "extraction": extraction,  # Propagate the updated extraction
        "answer": f"Are you sure you want to {intent} this {record_type}?{preview_str}{updates_str} (y/n)",
    }


def response_formatter(state):
    """Final formatting node — ensures answer is set."""
    if state.get("error"):
        return {"answer": f"Error: {state.get('error')}"}

    if state.get("saved_record_ids"):
        count = len(state.get("saved_record_ids"))
        return {"answer": f"Successfully created {count} record(s)."}

    if state.get("updated_record_id"):
        return {"answer": f"Record #{state.get('updated_record_id')} updated successfully."}

    if state.get("deleted_record_ids"):
        count = len(state.get("deleted_record_ids"))
        return {"answer": f"Successfully deleted {count} record(s)."}
        
    if state.get("deleted_record_id"):
        return {"answer": f"Record #{state.get('deleted_record_id')} deleted successfully."}

    if state.get("query_result") is not None:
        return {}  # query_result is rendered directly by the CLI

    if state.get("answer"):
        return {}  # answer already set (e.g., by confirmation)

    return {"answer": "Operation completed."}


# ── Build the graph ────────────────────────────────────────────

graph = StateGraph(State)

# Nodes
graph.add_node("primary_classifier", primary_classifier)
graph.add_node("extractor", extractor)
graph.add_node("record_saver", record_saver)
graph.add_node("record_updater", record_updater)
graph.add_node("record_deleter", record_deleter)
graph.add_node("query_executor", query_executor)
graph.add_node("analytics_query_executor", analytics_query_executor)
graph.add_node("confirmation_handler", confirmation_handler)
graph.add_node("update_details_handler", update_details_handler)
graph.add_node("request_confirmation", request_confirmation)
graph.add_node("response_formatter", response_formatter)

# Edges
graph.add_conditional_edges(START, check_confirmation, {
    "confirmation_handler": "confirmation_handler",
    "update_details_handler": "update_details_handler",
    "primary_classifier": "primary_classifier",
    "request_confirmation": "request_confirmation",
})

graph.add_conditional_edges("primary_classifier", primary_router, {
    "extractor": "extractor",
    "analytics_query_executor": "analytics_query_executor",
    "response_formatter": "response_formatter",
})

graph.add_conditional_edges("extractor", extractor_router, {
    "record_saver": "record_saver",
    "request_confirmation": "request_confirmation",
    "query_executor": "query_executor",
    "response_formatter": "response_formatter",
})

graph.add_conditional_edges("confirmation_handler", confirmation_router, {
    "record_deleter": "record_deleter",
    "record_updater": "record_updater",
    "response_formatter": "response_formatter",
})

graph.add_edge("update_details_handler", "request_confirmation")
graph.add_edge("request_confirmation", "response_formatter")
graph.add_edge("record_saver", "response_formatter")
graph.add_edge("record_updater", "response_formatter")
graph.add_edge("record_deleter", "response_formatter")
graph.add_edge("query_executor", "response_formatter")
graph.add_edge("analytics_query_executor", "response_formatter")
graph.add_edge("response_formatter", END)

# Compile
compiled_graph = graph.compile()
