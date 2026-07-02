# Task

Extract account setup details.

## Rules

- Account = bank, cash, wallet, or any named money place.
- Opening balance defaults to 0 if user does not specify.
- Keep account name exactly as mentioned.
- Return JSON only.

## Output Schema

```python
class CreateAccount(BaseModel):
    action: Literal["create"]
    records: list[AccountInput]
```
