from pathlib import Path
from llms import extractor_llm
from models.create_record_model import CreateRecord
from langchain_core.messages import SystemMessage, HumanMessage

from langchain_core.prompts import ChatPromptTemplate

EXTRACTION_PROMPT = Path("prompts/extract_create_record.md").read_text()


record_extraction_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=EXTRACTION_PROMPT),
        ("human", "{user_input}"),
    ]
)


def create_record_extractor(state):
    structured_llm = extractor_llm.with_structured_output(CreateRecord)

    prompts = record_extraction_prompt.invoke({"user_input": state.raw_text})

    result = structured_llm.invoke(prompts)

    return {"extraction": result}
