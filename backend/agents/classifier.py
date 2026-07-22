"""Primary router and classifier for WhatsMyNote."""

from langchain_core.messages import HumanMessage, SystemMessage
from backend.llms import get_extractor_llm
from backend.core.memory import ephemeral_reset
from pydantic import BaseModel, Field, AliasChoices

VALID_INTENTS = {"create", "update", "delete", "query", "unknown"}
VALID_RECORD_TYPES = {"lending", "expense", "account", "budget", "income", "transfer", "unknown"}

PRIMARY_PROMPT = """\
You are the primary financial router for WhatsMyNote.

Analyze the user's message and determine two things:
1. The INTENT of the message (create, update, delete, query, or unknown).
2. The RECORD TYPE the message is referring to.

## Intent Definitions
- create: Recording a PAST, COMPLETED financial event. (e.g. Lent Rahul 500, Spent 200, Received salary, Transferred 500, Sumit paid me back 31)
- update: Modifying an existing record. (e.g. Actually it was 600, Change the category, Fix the amount)
- delete: Removing a record. (e.g. Delete the last expense, Delete my lending records, Remove the account)
- query: Asking for information or analytics. (e.g. How much did I spend?, Show pie chart, Trend of expenses)
- unknown: Asking something unrelated, stating a future desire/unfulfilled need (e.g. "I need a beer", "I want to buy a laptop"), or gibberish.

## Record Type Definitions
- lending: Borrowing, lending, or paying back money (e.g. Lent Rahul 500, Sumit paid me 31, Who owes me?, Rahul returned the money)
- expense: Spending money on goods/services (e.g. Spent 200, Bought a laptop)
- income: Receiving money from standard sources like salary or business (e.g. Got salary, Made a sale)
- transfer: Moving money between own accounts (e.g. Transferred to SBI)
- budget: Setting limits (Set budget for groceries)
- account: Managing bank accounts/balances (Add account SBI)
- unknown: If the record type is unclear or not one of the above.

If the user uses pronouns (that, it, this), refer to the Context below:
{context}

Respond ONLY with a valid JSON object matching the requested schema. Use exactly these keys: "intent" and "record_type".
Example:
{{"intent": "create", "record_type": "expense"}}
"""

class ClassificationResult(BaseModel):
    intent: str = Field(description="create, update, delete, query, or unknown")
    record_type: str = Field(
        alias="recordType", 
        validation_alias=AliasChoices('record_type', 'recordType'),
        description="expense, income, lending, transfer, budget, account, or unknown"
    )

def _build_context_string(state) -> str:
    intent = state.get("intent")
    record_type = state.get("record_type")
    
    if intent or record_type:
        return f"Previous turn was {intent or 'unknown'} on {record_type or 'unknown'}."
    return "No previous context."

def primary_classifier(state):
    """Classify user intent and record type in a single LLM call."""
    context_str = _build_context_string(state)
    prompt = PRIMARY_PROMPT.format(context=context_str)

    llm = get_extractor_llm().with_structured_output(ClassificationResult, method="json_mode")
    
    try:
        result: ClassificationResult = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=state.get("raw_text", "")),
        ])
    except Exception as e:
        error_str = str(e)
        import re
        import json
        match = re.search(r"\{.*\}", error_str, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                result = ClassificationResult(**data)
            except Exception:
                return {"error": f"Failed to parse LLM output: {error_str}"}
        else:
            return {"error": f"Failed to parse LLM output: {error_str}"}

    intent = result.intent.strip().lower()
    record_type = result.record_type.strip().lower()

    if intent not in VALID_INTENTS:
        intent = "unknown"
    if record_type not in VALID_RECORD_TYPES:
        record_type = "unknown"

    # Reset all ephemeral fields at the start of every new turn
    updates = ephemeral_reset()
    updates["intent"] = intent
    updates["record_type"] = record_type
    
    if intent == "unknown":
        updates["error"] = "I am a financial assistant and can only help you with managing your finances."
        
    return updates

def primary_router(state):
    """Route after primary classification."""
    if state.get("error"):
        return "response_formatter"
        
    intent = state.get("intent")
    
    if intent in {"create", "update", "delete"}:
        return "extractor"
    if intent == "query":
        return "analytics_query_executor"
        
    return "response_formatter"
