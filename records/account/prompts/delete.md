# Task

Extract account delete details.

## Rules

- Use `last` for most recent account.
- Use `account` when user names one.
- Return JSON only.

## Output Schema

```python
class DeleteAccount(BaseModel):
    action: str = "delete"
    selector: RecordSelector
```
