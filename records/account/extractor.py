from datetime import date, timedelta
from pathlib import Path
import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from llms import extractor_llm
from records.account.models import (
    CreateAccount,
    UpdateAccount,
    DeleteAccount,
    QueryAccount,
)

CREATE_PROMPT = Path("records/account/prompts/create.md").read_text()
UPDATE_PROMPT = Path("records/account/prompts/update.md").read_text()
DELETE_PROMPT = Path("records/account/prompts/delete.md").read_text()
QUERY_PROMPT = Path("records/account/prompts/query.md").read_text()


def _extract(prompt: str, schema, user_input: str):
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    date_context = (
        f"Today's date is {today.isoformat()}. "
        f"Yesterday was {yesterday}. "
        "If no date is mentioned by user, use today's date.\n\n"
    )

    result = extractor_llm.invoke(
        [SystemMessage(content=date_context + prompt), HumanMessage(content=user_input)]
    )

    content = result.content.strip()
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if match:
        content = match.group(0)

    try:
        payload = json.loads(content)
        return schema.model_validate(payload)
    except Exception:
        if schema is DeleteAccount:
            return schema.model_validate(
                {"action": "delete", "selector": {"target": "last"}}
            )
        raise


def create_extractor(state):
    return {"extraction": _extract(CREATE_PROMPT, CreateAccount, state.raw_text)}


def update_extractor(state):
    return {"extraction": _extract(UPDATE_PROMPT, UpdateAccount, state.raw_text)}


def delete_extractor(state):
    return {"extraction": _extract(DELETE_PROMPT, DeleteAccount, state.raw_text)}


def query_extractor(state):
    return {"extraction": _extract(QUERY_PROMPT, QueryAccount, state.raw_text)}
