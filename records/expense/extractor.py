from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from records.expense.models import CreateExpense

from llms import extractor_llm

CREATE_PROMPT = Path("records/expense/prompts/create.md").read_text()


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
            CreateExpense,
            state.raw_text,
        )
    }
