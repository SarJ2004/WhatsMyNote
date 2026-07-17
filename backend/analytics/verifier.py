from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.llms import get_evaluator_llm


class AnalyticsReview(BaseModel):
    approved: bool = Field(description="True when SQL result matches the user request.")
    confidence: int = Field(
        ge=0,
        le=100,
        description="Confidence that the SQL answer is correct.",
    )
    reason: str = Field(description="Short explanation for the judgment.")
    revised_sql: str | None = Field(
        default=None,
        description="Optional corrected SQL if the original query looks wrong.",
    )
    rationale: str | None = Field(
        default=None,
        description="Short note for why revised SQL was suggested.",
    )
    revised_chart_config: dict | None = Field(
        default=None,
        description="Provide a completely revised chart config (matching ChartConfig schema) if the original is missing, invalid, or inappropriate for the user's request. Keep it null if the original chart config is fine."
    )


def _preview_rows(rows: Any, limit: int = 5) -> str:
    if rows is None:
        return "[]"

    if isinstance(rows, list):
        return json.dumps(rows[:limit], default=str, ensure_ascii=False)

    return json.dumps(rows, default=str, ensure_ascii=False)


def review_sql_result(question: str, sql: str, rows: Any, chart_config: Any = None) -> AnalyticsReview:
    structured_llm = get_evaluator_llm().with_structured_output(AnalyticsReview)
    
    chart_text = ""
    if chart_config:
        if hasattr(chart_config, "model_dump_json"):
            chart_text = f"Proposed Chart Configuration:\n{chart_config.model_dump_json(indent=2)}\n\n"
        else:
            chart_text = f"Proposed Chart Configuration:\n{json.dumps(chart_config, indent=2)}\n\n"
        
    messages = [
        SystemMessage(
            content=(
                "You review read-only SQL answers and their proposed charting configurations. "
                "Decide whether SQL answers user question well and if the chart_config makes sense for the result shape. "
                "If result looks wrong or chart_config is invalid for the columns returned, provide revised_sql and rationale. "
                "If the chart_config is missing when the user explicitly asked for a chart, or if the x_axis/y_axis do not perfectly match the SQL result keys, you MUST provide a revised_chart_config. "
                "Return concise judgment only."
            )
        ),
        HumanMessage(
            content=(
                f"User question:\n{question}\n\n"
                f"SQL:\n{sql}\n\n"
                f"Result preview:\n{_preview_rows(rows)}\n\n"
                f"{chart_text}"
            )
        ),
    ]

    try:
        return structured_llm.invoke(messages)
    except Exception as e:
        error_str = str(e)
        import re
        match = re.search(r"\{.*\}", error_str, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return AnalyticsReview(**data)
            except Exception:
                pass
                
        return AnalyticsReview(
            approved=False,
            confidence=0,
            reason=f"Verifier failed to parse LLM output: {error_str}"
        )
