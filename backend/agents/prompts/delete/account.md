# Task

Extract account delete details.

## Rules

- **CRITICAL ANTI-HALLUCINATION**: If the user's input is a generic command like "update my budgets" or "delete an expense" and DOES NOT explicitly name a specific target (e.g., it doesn't say "the last one", "for food", "to walmart"), you MUST output EXACTLY `{}`. DO NOT guess a selector. DO NOT use the example below. Output `{}` so the system can show the user a search menu.

- Only use `last` if the user explicitly refers to 'it', 'that', 'this', 'the record', or 'last/previous'. Do NOT use `last` just because a target is missing.
- Use `account` when user names one.
- If user refers to the default account, resolve that account name.
- Return JSON only.

## Output Schema

```json
{
    "action": "delete",
    "selector": {
        "target": "last"
    }
}
```