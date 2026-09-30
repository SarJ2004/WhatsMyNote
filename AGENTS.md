# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Correct entries that work proves wrong; add new ones only by deliberate maintainer choice, never as routine task output.

## Engine

- Tests need a disposable Postgres: point `WMN_TEST_DSN` at it (default in `tests/support.py`), then `uv run pytest`. Every test rebuilds the schema, so never aim it at a shared or hosted database.
- `supabase/migrations/` is the only schema. `0001` drops and recreates; every later migration is applied over a live database, so it must be additive and idempotent (`if not exists`, `drop policy if exists`).
- The model never writes SQL or sees a table name, and the caller's model key lives only for its request. Keep both true: see the module docstrings in `engine/intent.py` and `engine/api.py`.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
