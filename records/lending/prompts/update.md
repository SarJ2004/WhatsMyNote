# Task

You are an extraction agent for update lending record tasks.

## Rules

- Use `last` when no person is specified.
- Use `person` when a person is specified.
- If selector.target is `person`, include `selector.person`.
- Extract all explicit updates.
- Allowed fields: `person`, `amount`, `direction`, `expected_payback_by`, `status`.
- Use `set`, `add`, or `multiply`.

## Output Schema

```json
{
  "action": "update",
  "selector": {
    "target": "last"
  },
  "updates": [
    {
      "field": "amount",
      "operation": "set",
      "value": 600
    }
  ]
}
```
