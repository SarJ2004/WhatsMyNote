from typing import Optional
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from backend.analytics.schema_context import schema_context_for_question, select_tables
from backend.llms import get_extractor_llm

ANALYTICS_PROMPT = (Path(__file__).parent / "prompts" / "sql.md").read_text()

def plan_sql(question: str):
    schema_context = schema_context_for_question(question)
    messages = [
        SystemMessage(
            content=ANALYTICS_PROMPT + "\n\nRelevant schema:\n" + schema_context
        ),
        HumanMessage(content=question),
    ]

    from backend.analytics.models import AnalyticsSQL
    
    llm = get_extractor_llm().with_structured_output(AnalyticsSQL, method="json_mode")
    result = llm.invoke(messages)
    
    if result.error:
        raise ValueError(result.error)
        
    if not result.sql:
        raise ValueError("Could not generate a valid SQL query.")
    return result.sql, result.chart_config, select_tables(question)
