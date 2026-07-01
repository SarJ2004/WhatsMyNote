from datetime import date, timedelta
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from llms import extractor_llm
from records.income.models import CreateIncome, UpdateIncome, DeleteIncome, QueryIncome

CREATE_PROMPT = Path("records/income/prompts/create.md").read_text()
UPDATE_PROMPT = Path("records/income/prompts/update.md").read_text()
DELETE_PROMPT = Path("records/income/prompts/delete.md").read_text()
QUERY_PROMPT = Path("records/income/prompts/query.md").read_text()


def _extract(prompt: str, schema, user_input: str):
    structured_llm = extractor_llm.with_structured_output(schema)

    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()

    date_context = (
        f"Today's date is {today.isoformat()}. "
        f"Yesterday was {yesterday}. "
        "If no date is mentioned by the user, use today's date.\n\n"
    )

    messages = [
        SystemMessage(content=date_context + prompt),
        HumanMessage(content=user_input),
    ]

    return structured_llm.invoke(messages)


def create_extractor(state):
    return {"extraction": _extract(CREATE_PROMPT, CreateIncome, state.raw_text)}


def update_extractor(state):
    return {"extraction": _extract(UPDATE_PROMPT, UpdateIncome, state.raw_text)}


def delete_extractor(state):
    return {"extraction": _extract(DELETE_PROMPT, DeleteIncome, state.raw_text)}


def query_extractor(state):
    return {"extraction": _extract(QUERY_PROMPT, QueryIncome, state.raw_text)}