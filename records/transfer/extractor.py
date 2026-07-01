from datetime import date, timedelta
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from llms import extractor_llm
from records.transfer.models import CreateTransfer, UpdateTransfer, DeleteTransfer, QueryTransfer

CREATE_PROMPT = Path("records/transfer/prompts/create.md").read_text()
UPDATE_PROMPT = Path("records/transfer/prompts/update.md").read_text()
DELETE_PROMPT = Path("records/transfer/prompts/delete.md").read_text()
QUERY_PROMPT = Path("records/transfer/prompts/query.md").read_text()


def _extract(prompt: str, schema, user_input: str):
    structured_llm = extractor_llm.with_structured_output(schema)

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    date_context = (
        f"Today's date is {today.isoformat()}. "
        f"Yesterday was {yesterday}. "
        "If no date is mentioned by user, use today's date.\n\n"
    )

    messages = [
        SystemMessage(content=date_context + prompt),
        HumanMessage(content=user_input),
    ]

    return structured_llm.invoke(messages)


def create_extractor(state):
    return {"extraction": _extract(CREATE_PROMPT, CreateTransfer, state.raw_text)}


def update_extractor(state):
    return {"extraction": _extract(UPDATE_PROMPT, UpdateTransfer, state.raw_text)}


def delete_extractor(state):
    return {"extraction": _extract(DELETE_PROMPT, DeleteTransfer, state.raw_text)}


def query_extractor(state):
    return {"extraction": _extract(QUERY_PROMPT, QueryTransfer, state.raw_text)}