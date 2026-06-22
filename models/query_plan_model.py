from pydantic import BaseModel, Field
from typing import Literal


class QueryPlan(BaseModel):
    operation: Literal["sum", "count", "list", "difference", "net_balance", "list"]

    people: list[str] = Field(default_factory=list)
    metric: Literal["all", "lent", "borrowed", "outstanding"] = "all"
    filters: dict[str, str] = Field(default_factory=dict)
