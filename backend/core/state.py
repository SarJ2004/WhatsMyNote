"""Unified State model for the LangGraph expense tracker."""

import operator
from typing import TypedDict, Annotated, Optional, Any


def replace(a: Any, b: Any) -> Any:
    """Always replace the current state with the new state, even if new state is None."""
    return b


class State(TypedDict):
    """Single state object flowing through the entire graph.
    
    Using TypedDict ensures LangGraph cleanly overwrites fields instead of merging them improperly.
    """

    # ── User input ──────────────────────────────────────────────
    raw_text: str

    # ── Classification ──────────────────────────────────────────
    intent: Annotated[Optional[str], replace]            # create | update | delete | query
    record_type: Annotated[Optional[str], replace]       # expense | income | lending | ...

    # ── Extraction (raw JSON dict from LLM) ─────────────────────
    extraction: Annotated[Optional[dict], replace]

    # ── Confirmation flow (short-term memory) ───────────────────
    awaiting_confirmation: Annotated[bool, replace]

    # ── HITL fuzzy search ───────────────────────────────────────
    search_results: Annotated[list[dict], replace]
    awaiting_selection: Annotated[bool, replace]
    selected_record_id: Annotated[Optional[int], replace]
    selected_record_ids: Annotated[Optional[list[int]], replace]
    awaiting_update_details: Annotated[bool, replace]

    # ── Execution results (ephemeral — reset each turn) ─────────
    saved_record_ids: Annotated[list[int], replace]
    updated_record_id: Annotated[Optional[int], replace]
    deleted_record_id: Annotated[Optional[int], replace]
    deleted_record_ids: Annotated[Optional[list[int]], replace]
    query_result: Annotated[Optional[object], replace]
    answer: Annotated[Optional[str], replace]
    error: Annotated[Optional[str], replace]
    record_preview: Annotated[Optional[object], replace]

    # ── Budget alerts ───────────────────────────────────────────
    budget_alerts: Annotated[list[str], replace]

    # ── Analytics ───────────────────────────────────────────────
    analytics_mode: Annotated[bool, replace]
    analytics_sql: Annotated[Optional[str], replace]
    analytics_review: Annotated[Optional[str], replace]
    chart_config: Annotated[Optional[dict], replace]
