import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from analytics.models import AnalyticsSQL
from analytics.schema_context import schema_context_for_question, select_tables
from llms import extractor_llm

ANALYTICS_PROMPT = Path("analytics/prompts/sql.md").read_text()


def _parse_sql_payload(content: str) -> str:
    text = content.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return content.strip()

    if isinstance(payload, dict) and "sql" in payload:
        return str(payload["sql"])

    return content.strip()


def plan_sql(question: str):
    schema_context = schema_context_for_question(question)
    messages = [
        SystemMessage(content=ANALYTICS_PROMPT + "\n\nRelevant schema:\n" + schema_context),
        HumanMessage(content=question),
    ]

    result = extractor_llm.invoke(messages)
    sql = _parse_sql_payload(result.content)
    AnalyticsSQL(sql=sql)
    return sql, select_tables(question)