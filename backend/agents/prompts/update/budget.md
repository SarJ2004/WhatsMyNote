# Task

Extract budget update.

## Rules

- **CRITICAL ANTI-HALLUCINATION**: If the user's input is a generic command like "update my budgets" or "delete an expense" and DOES NOT explicitly name a specific target (e.g., it doesn't say "the last one", "for food", "to walmart"), you MUST output EXACTLY `{}`. DO NOT guess a selector. DO NOT use the example below. Output `{}` so the system can show the user a search menu.

- Only use `last` if the user explicitly refers to 'it', 'that', 'this', 'the record', or 'last/previous'. Do NOT use `last` just because a target is missing.
- Use `category` when user names one.
- Use category `Overall` for total budget.
- Allowed fields: `category`, `amount`, `period`, `notes`.
- Return JSON only.

## Output Schema

```json
{
	"action": "update",
	"selector": {
		"target": "category",
		"category": "Overall"
	},
	"updates": [
		{
			"field": "amount",
			"operation": "set",
			"value": 60000
		}
	]
}
```