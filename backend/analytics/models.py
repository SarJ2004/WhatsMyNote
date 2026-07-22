from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class ChartType(str, Enum):
    BAR = "bar"
    LINE = "line"
    SCATTER = "scatter"
    PIE = "pie"
    DONUT = "donut"
    NONE = "none"


class ChartConfig(BaseModel):
    chart_type: ChartType = Field(description="The type of chart to display.")
    x_axis: str = Field(description="The exact column name for the x-axis labels.")
    y_axis: str = Field(description="The exact column name for the y-axis values.")
    title: str = Field(description="A concise title for the chart.")
    color: Optional[str] = Field(
        default=None, 
        description="A plotext color (e.g., 'red', 'green', 'blue', 'yellow') or 'diverse' for multi-colored bars."
    )


class AnalyticsSQL(BaseModel):
    sql: Optional[str] = Field(
        default=None, 
        description="Safe read-only SQL query."
    )
    chart_config: Optional[ChartConfig] = Field(
        default=None,
        description="Optional chart configuration if the data warrants visualization."
    )
    error: Optional[str] = Field(
        default=None,
        description="If the question is gibberish or unanswerable, provide an explanation here."
    )
