"""Generic extractor — loads the right prompt and model for any (intent, record_type) pair."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from backend.llms import get_extractor_llm
from backend.records.models import MODEL_REGISTRY
from backend.records.search import search_recent_records


def _load_prompt(intent: str, record_type: str) -> str:
    """Load the prompt file for a given intent and record type."""
    prompt_path = Path(__file__).parent / "prompts" / intent / f"{record_type}.md"
    if not prompt_path.exists():
        return f"Extract the {intent} details for a {record_type} record. Return valid JSON."
    return prompt_path.read_text()


def _date_context() -> str:
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    return (
        f"Today's date is {today.isoformat()}. "
        f"Yesterday was {yesterday}. "
        "If no date is mentioned by the user, do not set a date field.\n\n"
    )


def extractor(state):
    """Generic extraction node — dispatches based on state.get("intent") + state.get("record_type")."""
    intent = state.get("intent")
    record_type = state.get("record_type")

    if not intent or not record_type:
        return {"error": "Missing intent or record type for extraction."}

    model_cls = MODEL_REGISTRY.get((intent, record_type))
    if model_cls is None:
        return {"error": f"No model registered for ({intent}, {record_type})."}

    prompt = _load_prompt(intent, record_type)

    messages = [
        SystemMessage(content=_date_context() + prompt),
        HumanMessage(content=state.get("raw_text")),
    ]

    try:
        result = get_extractor_llm().invoke(messages)
        content = result.content.strip()

        # Extract JSON from response
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            content = match.group(0)

        payload = json.loads(content)

        # Validate against the Pydantic model
        validated = model_cls.model_validate(payload)

        return {"extraction": validated.model_dump(mode="json")}

    except Exception as e:
        # For delete/update with ambiguous targets, offer HITL search
        if intent in ("delete", "update"):
            results = search_recent_records(record_type)
            if results:
                return {
                    "search_results": results,
                    "awaiting_selection": True,
                    "answer": f"I couldn't determine which {record_type} to {intent}. Please select from the list below.",
                }
        return {"error": f"Failed to extract details: {e}"}


def extractor_router(state):
    """Route after extraction — send creates to saver, updates/deletes to confirmation."""
    if state.get("error"):
        return "response_formatter"

    if state.get("awaiting_selection"):
        return "response_formatter"

    intent = state.get("intent")

    if intent == "create":
        return "record_saver"
    elif intent in ("update", "delete"):
        return "request_confirmation"
    elif intent == "query":
        return "query_executor"

    return "response_formatter"
