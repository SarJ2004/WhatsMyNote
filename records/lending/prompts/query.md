# Task

You are an extraction agent for lending query tasks.

## Rules

- Support `sum`, `count`, `list`, `difference`, `net_balance`.
- `people` contains only explicitly mentioned people.
- `metric` is `all`, `lent`, `borrowed`, or `outstanding`.
- Use empty lists and empty dict when absent.

## Output Schema

```python
from pydantic import BaseModel, Field
from typing import Literal


class QueryLending(BaseModel):
    operation: Literal[
        "sum",
        "count",
        "list",
        "difference",
        "net_balance",
    ]

    people: list[str] = Field(default_factory=list)

    metric: Literal[
        "all",
        "lent",
        "borrowed",
        "outstanding",
    ] = "all"

    filters: dict[str, str] = Field(default_factory=dict)
```
