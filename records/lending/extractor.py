from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from records.lending.models import (
    CreateLending,
    UpdateLending,
    DeleteLending,
    QueryLending,
)

from llms import extractor_llm

CREATE_PROMPT = Path("records/lending/prompts/create.md").read_text()
UPDATE_PROMPT = Path("records/lending/prompts/update.md").read_text()
DELETE_PROMPT = Path("records/lending/prompts/delete.md").read_text()
QUERY_PROMPT = Path("records/lending/prompts/query.md").read_text()


def _extract(prompt: str, schema, user_input: str):
    structured_llm = extractor_llm.with_structured_output(schema)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=prompt),
            ("human", "{user_input}"),
        ]
    )

    messages = prompt.invoke({"user_input": user_input})

    return structured_llm.invoke(messages)


def create_extractor(state):
    return {
        "extraction": _extract(
            CREATE_PROMPT,
            CreateLending,
            state.raw_text,
        )
    }


def update_extractor(state):
    return {
        "extraction": _extract(
            UPDATE_PROMPT,
            UpdateLending,
            state.raw_text,
        )
    }


def delete_extractor(state):
    return {
        "extraction": _extract(
            DELETE_PROMPT,
            DeleteLending,
            state.raw_text,
        )
    }


def query_extractor(state):
    return {
        "extraction": _extract(
            QUERY_PROMPT,
            QueryLending,
            state.raw_text,
        )
    }
