# Task

Extract budget query.

## Rules

- Support `sum`, `count`, `list`, `average`, `max`, `min`, `remaining`, `variance`.
- `Overall` means total budget across all spend.
- Use `remaining` for left budget, `variance` for actual minus budget view.
- Use `filters` for period or date constraints when explicit.
- Return JSON only.

## Output Schema

```json
{
	"operation": "remaining",
	"metric": "remaining",
	"categories": ["Overall"],
	"filters": {"month": "current"}
}
```
