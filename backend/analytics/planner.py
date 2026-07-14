import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from backend.analytics.models import AnalyticsSQL
from backend.analytics.schema_context import schema_context_for_question, select_tables
from backend.llms import get_extractor_llm

ANALYTICS_PROMPT = (Path(__file__).parent / "prompts" / "sql.md").read_text()


from typing import Optional

def _parse_sql_payload(content: str) -> tuple[str | None, Optional[dict], Optional[str]]:
    text = content.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return content.strip(), None, None

    if isinstance(payload, dict):
        if payload.get("error"):
            return None, None, payload.get("error")
        if payload.get("sql"):
            return str(payload["sql"]), payload.get("chart_config"), None

    return content.strip(), None, None


def plan_sql(question: str):
    schema_context = schema_context_for_question(question)
    messages = [
        SystemMessage(
            content=ANALYTICS_PROMPT + "\n\nRelevant schema:\n" + schema_context
        ),
        HumanMessage(content=question),
    ]

    result = get_extractor_llm().invoke(messages)
    sql, chart_config_dict, error = _parse_sql_payload(result.content)
    
    if error:
        raise ValueError(error)
        
    if not sql:
        raise ValueError("Could not generate a valid SQL query.")
        
    chart_config = None
    if chart_config_dict:
        try:
            from backend.analytics.models import ChartConfig
            chart_config = ChartConfig(**chart_config_dict)
        except Exception:
            chart_config = chart_config_dict

    # We skip strict AnalyticsSQL validation here because we want to pass
    # potentially invalid chart configs down to the verifier for auto-correction.
    return sql, chart_config, select_tables(question)
