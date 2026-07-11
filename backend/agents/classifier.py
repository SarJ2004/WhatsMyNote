"""Intent and record type classifier — merged into a single module."""

from langchain_core.messages import HumanMessage, SystemMessage
from backend.llms import get_evaluator_llm
from backend.core.memory import ephemeral_reset

VALID_INTENTS = {"create", "update", "delete", "query"}

VALID_RECORD_TYPES = {"lending", "expense", "account", "budget", "income", "transfer"}

INTENT_PROMPT = """\
You are classifying a user's message.

Return exactly one word:

create
update
delete
query

Definitions

create — The user is recording a NEW financial event.
Examples: Lent Rahul 500, Spent 200 on pizza, Received salary, Transferred 500, Set budget of groceries to 1000

update — The user is modifying an existing record.
Examples: Actually it was 600, Mark it as paid, Increase it by 200

delete — The user wants to remove a record.
Examples: Delete the last expense, Remove Rahul's loan

query — The user is asking for information.
Examples: How much did I spend?, Show my expenses, Who owes me money?

If the user is using pronouns (that, it, this), refer to the Context below:
{context}

Return only one word."""

RECORD_TYPE_PROMPT = """\
You are a financial record classifier.

Determine the TYPE of financial record in the user's message.
Ignore whether the user is creating, updating, deleting, or querying.
Only determine the record type.

Return exactly one word:

lending
expense
income
transfer
budget
account

Do not explain. Do not output JSON. Do not output markdown.

Examples

Lent Rahul 500 → lending
Borrowed 500 from Amit → lending
Rahul repaid me → lending
Delete the last lending record → lending
Who owes me money? → lending
How much have I lent? → lending

Spent 200 → expense
Paid 500 for groceries → expense
Bought a laptop → expense
Delete the last expense → expense
How much did I spend? → expense
Show all expenses → expense

Received salary → income
Got my monthly salary → income
Delete the last income → income
Show all income → income

Transferred 500 to SBI → transfer
Sent money to HDFC account → transfer
Delete the last transfer → transfer
Show my transfers → transfer

Set budget of groceries to 1000 → budget
Create a budget for selfcare for 400 → budget
Delete grocery budget → budget
Show my budgets → budget
update my budgets → budget

Add account SBI → account
Set opening balance of HDFC to 5000 → account
Delete my SBI account → account
Show my accounts → account
need to update my accounts → account

If the user is using pronouns (that, it, this), refer to the Context below:
{context}

Return only one word."""


def _build_context_string(state) -> str:
    # Use the previous intent and record_type if available in state before reset
    intent = state.get("intent")
    record_type = state.get("record_type")
    
    if intent or record_type:
        return f"Previous turn was {intent or 'unknown'} on {record_type or 'unknown'}."
    return "No previous context."


def intent_classifier(state):
    """Classify user intent and reset ephemeral state for new turn."""
    context_str = _build_context_string(state)
    prompt = INTENT_PROMPT.format(context=context_str)

    result = get_evaluator_llm().invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state.get("raw_text", "")),
    ])

    intent = result.content.strip().lower()

    if intent not in VALID_INTENTS:
        return {"error": f"Could not understand your intent. Got: {intent}"}

    # Reset all ephemeral fields at the start of every new turn
    updates = ephemeral_reset()
    updates["intent"] = intent
    return updates


def record_type_classifier(state):
    """Classify the record type from the user's message."""
    context_str = _build_context_string(state)
    prompt = RECORD_TYPE_PROMPT.format(context=context_str)

    result = get_evaluator_llm().invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=state.get("raw_text", "")),
    ])

    record_type = result.content.strip().lower()

    if record_type not in VALID_RECORD_TYPES:
        return {"error": f"Could not determine record type. Got: {record_type}"}

    return {"record_type": record_type}


def intent_router(state):
    """Route after intent classification."""
    if state.get("error"):
        return "response_formatter"
    if state.get("intent") in {"create", "update", "delete"}:
        return "record_type_classifier"
    if state.get("intent") == "query":
        return "analytics_detector"
    return "response_formatter"


def record_type_router(state):
    """Route after record type classification."""
    if state.get("error"):
        return "response_formatter"

    intent = state.get("intent")
    record_type = state.get("record_type")

    if not intent or not record_type:
        return "response_formatter"

    return "extractor"
