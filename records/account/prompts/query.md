# Task

Extract account query details.

## Rules

- Support `sum`, `count`, `list`, `average`, `max`, `min`, `balance`.
- Use `balance` for current account balance.
- Extract account names only when explicit.
- Return JSON only.

## Output Schema

```python
class QueryAccount(BaseModel):
    operation: Literal["sum", "count", "list", "average", "max", "min", "balance"]
    metric: Literal["opening_balance", "balance"] = "balance"
    accounts: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
```
