# Task

Extract account query details.

## Rules

- Support `sum`, `count`, `list`, `average`, `max`, `min`, `balance`.
- Use `balance` for current account balance.
- `opening_balance` means stored opening amount.
- If user asks for default account, keep `accounts` empty and set `filters.is_default = "true"`.
- Extract account names only when explicit.
- Use `filters.currency` when user names currency.
- Return JSON only.

## Output Schema

```json
{
    "operation": "balance",
    "metric": "balance",
    "accounts": ["SBI"],
    "filters": {}
}
```
