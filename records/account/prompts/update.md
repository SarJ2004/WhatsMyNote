# Task

Extract account update details.

## Rules

- Use `last` when user means most recent account setup.
- Use `account` when user names one.
- Allowed fields: `name`, `opening_balance`, `currency`, `notes`.
- Return JSON only.

## Output Schema

```python
class UpdateAccount(BaseModel):
    action: Literal["update"]
    selector: RecordSelector
    updates: list[AccountFieldUpdate]
```
