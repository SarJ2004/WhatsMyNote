from pathlib import Path
from llms import extractor_llm
from models.query_plan_model import QueryPlan

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

EXTRACTION_PROMPT = Path("prompts/extract_query.md").read_text()

query_extraction_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=EXTRACTION_PROMPT),
        ("human", "{user_input}"),
    ]
)


def query_extractor(state):
    structured_llm = extractor_llm.with_structured_output(QueryPlan)

    prompts = query_extraction_prompt.invoke({"user_input": state.raw_text})

    result = structured_llm.invoke(prompts)

    return {"extraction": result}
