import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from backend.analytics.models import AnalyticsSQL
from backend.analytics.schema_context import schema_context_for_question, select_tables
from backend.llms import get_extractor_llm

ANALYTICS_PROMPT = (Path(__file__).parent / "prompts" / "sql.md").read_text()


from typing import Optional

def _parse_sql_payload(content: str) -> tuple[str, Optional[dict]]:
    text = content.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return content.strip(), None

    if isinstance(payload, dict) and "sql" in payload:
        return str(payload["sql"]), payload.get("chart_config")

    return content.strip(), None


def plan_sql(question: str):
    schema_context = schema_context_for_question(question)
    messages = [
        SystemMessage(
            content=ANALYTICS_PROMPT + "\n\nRelevant schema:\n" + schema_context
        ),
        HumanMessage(content=question),
    ]

    result = get_extractor_llm().invoke(messages)
    sql, chart_config_dict = _parse_sql_payload(result.content)
    
    chart_config = None
    if chart_config_dict:
        try:
            from backend.analytics.models import ChartConfig
            chart_config = ChartConfig(**chart_config_dict)
        except Exception:
            pass

    AnalyticsSQL(sql=sql, chart_config=chart_config)
    return sql, chart_config, select_tables(question)
