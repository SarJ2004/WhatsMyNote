from pydantic import BaseModel, Field


class AnalyticsSQL(BaseModel):
    sql: str = Field(description="Safe read-only SQL query.")