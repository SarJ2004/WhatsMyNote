from typing import Literal
from pydantic import BaseModel, Field
from llms import evaluator_llm
from langchain_core.messages import SystemMessage, HumanMessage


class Intent(BaseModel):
    intent: Literal["query", "create", "update", "delete"] = Field(
        description="The intent of the user input"
    )


def intent_evaluator(state):
    """Evaluate the user input and determine if it's a 'query' or 'record' intent."""
    intent_evaluator_llm = evaluator_llm.with_structured_output(Intent)
    result = intent_evaluator_llm.invoke(
        [
            SystemMessage(content="""
You are an intent classifier for a lending/borrowing tracking application.

Classify the user's message into exactly one of:

- "create"
  User is creating a new lending/borrowing record.
  Examples:
  - Lent Sumit 500
  - Borrowed 200 from Rahul
  - Lent Rohan 1000 due next month

- "update"
  User is modifying an existing record.
  Examples:
  - Actually it was 600
  - Change Sumit's amount to 700
  - Mark Rahul as paid
  - Increase it by 200

- "delete"
  User wants to remove a record.
  Examples:
  - Delete that entry
  - Remove Sumit's record
  - Forget the last transaction

- "query"
  User is asking a question or requesting information.
  Examples:
  - How much does Sumit owe me?
  - Show my pending loans
  - What is 2+2?

Return only the intent.
"""),
            HumanMessage(content=state.raw_text),
        ],
    )
    return {"intent": result.intent}


def intent_router(state):
    """Route the user input as "query", or "record" intent."""
    if state.intent == "create":
        return "create_record_extractor"

    if state.intent == "update":
        return "update_record_extractor"

    if state.intent == "delete":
        return "delete_record_extractor"
    if state.intent == "query":
        return "query_extractor"
    else:
        return "END"
