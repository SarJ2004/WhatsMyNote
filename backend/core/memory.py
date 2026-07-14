"""Checkpointer setup and state reset helpers."""

import logging
# Suppress noisy msgpack deserialization warnings from LangGraph
logging.getLogger("langgraph.checkpoint.serde.jsonplus").setLevel(logging.ERROR)


def ephemeral_reset() -> dict:
    """Return a dict that resets all ephemeral/transient state fields.

    Call this at the start of every new turn (in the classifier node)
    so that stale results from previous turns don't bleed through.
    """
    return {
        "saved_record_ids": [],
        "updated_record_id": None,
        "deleted_record_id": None,
        "deleted_record_ids": None,
        "query_result": None,
        "answer": None,
        "error": None,
        "extraction": None,
        "record_type": None,
        "search_results": [],
        "awaiting_selection": False,
        "selected_record_id": None,
        "selected_record_ids": None,
        "awaiting_update_details": False,
        "budget_alerts": [],
        "analytics_mode": False,
        "analytics_sql": None,
        "analytics_review": None,
        "record_preview": None,
    }
