from pathlib import Path
from datetime import date, timedelta
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from records.expense.models import CreateExpense
from records.expense.models import UpdateExpense
from records.expense.models import DeleteExpense
from records.expense.models import QueryExpense

from llms import extractor_llm

CREATE_PROMPT = Path("records/expense/prompts/create.md").read_text()
UPDATE_PROMPT = Path("records/expense/prompts/update.md").read_text()
DELETE_PROMPT = Path("records/expense/prompts/delete.md").read_text()
QUERY_PROMPT = Path("records/expense/prompts/query.md").read_text()


def _extract(prompt: str, schema, user_input: str):
    structured_llm = extractor_llm.with_structured_output(schema)

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    date_context = (
        f"Today's date is {today.isoformat()}. "
        f"Yesterday was {yesterday}. "
        "If no date is mentioned by the user, do not update expense_date.\n\n"
    )

    messages = [
        SystemMessage(content=date_context + prompt),
        HumanMessage(content=user_input),
    ]

    return structured_llm.invoke(messages)


def create_extractor(state):
    return {
        "extraction": _extract(
            CREATE_PROMPT,
            CreateExpense,
            state.raw_text,
        )
    }


def update_extractor(state):
    return {
        "extraction": _extract(
            UPDATE_PROMPT,
            UpdateExpense,
            state.raw_text,
        )
    }


def delete_extractor(state):
    return {
        "extraction": _extract(
            QUERY_PROMPT,
            DeleteExpense,
            state.raw_text,
        )
    }


def query_extractor(state):
    return {
        "extraction": _extract(
            QUERY_PROMPT,
            QueryExpense,
            state.raw_text,
        )
    }
