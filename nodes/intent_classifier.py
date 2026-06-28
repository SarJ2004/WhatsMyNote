from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from llms import evaluator_llm


class Intent(BaseModel):
    intent: Literal["create", "update", "delete", "query"] = Field(
        description="The operation requested by the user."
    )


class RecordType(BaseModel):
    record_type: Literal[
        "lending",
        "expense",
        "income",
        "transfer",
    ] = Field(description="The financial record type.")


VALID_INTENTS = {
    "create",
    "update",
    "delete",
    "query",
}


def intent_evaluator(state):
    result = evaluator_llm.invoke(
        [
            SystemMessage(content="""
You are classifying a user's message.

Return exactly one word:

create
update
delete
query

Definitions

create
The user is recording a NEW financial event.

Examples

Lent Rahul 500
Spent 200 on pizza
Paid 900 for groceries
Received salary
Transferred 500

update
The user is modifying an existing record.

Examples

Actually it was 600
Mark it as paid
Increase it by 200

delete
The user wants to remove a record.

Examples

Delete the last expense
Remove Rahul's loan

query
The user is asking for information.

Examples

How much did I spend?
Show my expenses
Who owes me money?

Return only one word.
"""),
            HumanMessage(content=state.raw_text),
        ]
    )

    intent = result.content.strip().lower()

    if intent not in VALID_INTENTS:
        raise ValueError(f"Invalid intent: {intent}")

    return {"intent": intent}


VALID_RECORD_TYPES = {
    "lending",
    "expense",
    "income",
    "transfer",
}


def record_type_evaluator(state):
    result = evaluator_llm.invoke(
        [
            SystemMessage(content="""
You are a financial record classifier.

Return exactly one word.

lending
expense
income
transfer

Do not explain.
Do not output JSON.
Do not output markdown.

Examples:

Spent 200
expense

Borrowed 500
lending

Received salary
income

Transferred money
transfer
"""),
            HumanMessage(content=state.raw_text),
        ]
    )

    record_type = result.content.strip().lower()

    if record_type not in VALID_RECORD_TYPES:
        raise ValueError(f"Invalid record type: {record_type}")

    return {
        "record_type": record_type,
    }


def intent_router(state):
    """
    Route after intent classification.
    """

    if state.intent == "query":
        return "query_router"

    if state.intent in {"create", "update", "delete"}:
        return "record_type_evaluator"

    return "END"


def record_type_router(state):
    """
    Route after record type classification.
    """

    match (state.intent, state.record_type):

        case ("create", "lending"):
            return "create_lending_extractor"

        case ("create", "expense"):
            return "create_expense_extractor"

        case ("update", "lending"):
            return "update_lending_extractor"

        case ("update", "expense"):
            return "update_expense_extractor"

        case ("delete", "lending"):
            return "delete_lending_extractor"

        case ("delete", "expense"):
            return "delete_expense_extractor"

        case _:
            return "END"
