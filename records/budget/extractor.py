from datetime import date, timedelta
from pathlib import Path
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from llms import extractor_llm
from records.budget.models import CreateBudget, UpdateBudget, DeleteBudget, QueryBudget

CREATE_PROMPT = Path("records/budget/prompts/create.md").read_text()
UPDATE_PROMPT = Path("records/budget/prompts/update.md").read_text()
DELETE_PROMPT = Path("records/budget/prompts/delete.md").read_text()
QUERY_PROMPT = Path("records/budget/prompts/query.md").read_text()


def _extract(prompt: str, schema, user_input: str):
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    date_context = f"Today's date is {today.isoformat()}. Yesterday was {yesterday}.\n\n"

    result = extractor_llm.invoke([SystemMessage(content=date_context + prompt), HumanMessage(content=user_input)])
    content = result.content.strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        content = match.group(0)
    payload = json.loads(content)
    return schema.model_validate(payload)


def create_extractor(state):
    return {"extraction": _extract(CREATE_PROMPT, CreateBudget, state.raw_text)}


def update_extractor(state):
    return {"extraction": _extract(UPDATE_PROMPT, UpdateBudget, state.raw_text)}


def delete_extractor(state):
    return {"extraction": _extract(DELETE_PROMPT, DeleteBudget, state.raw_text)}


def query_extractor(state):
    return {"extraction": _extract(QUERY_PROMPT, QueryBudget, state.raw_text)}
