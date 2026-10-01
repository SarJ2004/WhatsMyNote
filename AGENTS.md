# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Tests: `uv run --with pytest python -m pytest -q` against a throwaway Postgres (`WMN_TEST_DSN`); setup in `CONTRIBUTING.md`. The tests drop and recreate tables, so never point them at a Supabase project.
- The schema lives only in `supabase/migrations/*.sql`; the engine's environment is exactly `.env.sample`.
- Publishing is tag-only (`release.yml`, `terminal-build.yml`); production deploy is manual (`render-deploy.yml`). Release steps: `CONTRIBUTING.md#releasing`.
- Commit as `sargedevx@gmail.com`, and keep employer names out of code, docs and commits.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
