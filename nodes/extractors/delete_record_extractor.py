from pathlib import Path
from llms import extractor_llm
from models.delete_record_model import DeleteRecord

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

EXTRACTION_PROMPT = Path("prompts/extract_delete_record.md").read_text()

update_record_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage(content=EXTRACTION_PROMPT),
        ("human", "{user_input}"),
    ]
)


def delete_record_extractor(state):
    structured_llm = extractor_llm.with_structured_output(DeleteRecord)

    prompts = update_record_prompt.invoke({"user_input": state.raw_text})

    result = structured_llm.invoke(prompts)

    return {"extraction": result}
