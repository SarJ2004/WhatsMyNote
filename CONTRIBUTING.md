# Contributing to WhatsMyNote

Thanks for helping. Bug reports, fixes and features are all welcome: open an
[issue](https://github.com/SarJ2004/WhatsMyNote/issues) or a pull request.

## Layout

| Path | What lives there |
|---|---|
| `engine/` | The stateless engine: parsing, money, rates, the ledger, queries, and the FastAPI app. |
| `web/index.html` | The website. One file, no build step; the engine serves it at `/`. |
| `whatsmynote/` | The terminal app published to PyPI. |
| `mcp_server/` | MCP tools over the engine. |
| `supabase/migrations/` | The schema, as plain SQL. It is the only description of the database. |
| `tests/` | The test suite. |

## Set up a checkout

You need Python 3.11+, [uv](https://docs.astral.sh/uv/), and Docker (or any local Postgres).

```bash
git clone https://github.com/SarJ2004/WhatsMyNote.git
cd WhatsMyNote
uv sync
```

## Run the tests

The tests need a throwaway Postgres database. They apply
`supabase/migrations/0001_isolation.sql` to it, which drops and recreates the
tables, so never point them at a database you care about, and never at a real
Supabase project.

Start one with Docker:

```bash
docker run -d --name wmn-test-pg -p 54329:5432 \
  -e POSTGRES_PASSWORD=wmn -e POSTGRES_DB=whatsmynote postgres:16
```

Then run the suite from the repository root:

```bash
uv run --with pytest python -m pytest -q
```

The tests connect to `postgresql://postgres:wmn@localhost:54329/whatsmynote` by
default. To use another database, set `WMN_TEST_DSN`:

```bash
WMN_TEST_DSN=postgresql://user:pass@localhost:5432/scratch uv run --with pytest python -m pytest -q
```

The suite needs no model key and no network: the model, Supabase sign-in, and
the rate service are all replaced by stubs. The same command runs in CI
(`.github/workflows/tests.yml`) on every pull request.

## Run the engine locally

```bash
cp .env.sample .env    # fill in your Supabase project's values
uv run --env-file .env uvicorn --factory engine.api:create_live_app --reload
```

To point the terminal at it, set `ENV=dev` (for example in `.env`) and run `uv run whatsmynote` in a
second terminal. `ENV=dev` makes the terminal use `http://127.0.0.1:8000`; the
Supabase project it signs in to is set in `whatsmynote/app/config.py`.

## Pull requests

- Keep changes focused, and add or update tests for any behaviour you change.
- Make sure `uv run --with pytest python -m pytest -q` passes.
- Write commit messages as [Conventional Commits](https://www.conventionalcommits.org)
  (`feat: ...`, `fix: ...`), so the generated release notes read well.
- A model key must never be stored, logged, or included in a response or error.
- Schema changes go in a new numbered file under `supabase/migrations/`.

## Releasing

Maintainers only. Publishing happens only when a version tag is pushed; a push
to `main` never publishes.

1. Bump `version` in `pyproject.toml`, run `uv lock`, and merge that to `main`.
2. Tag the merge commit with the same version and push the tag:
   ```bash
   git tag v0.3.0
   git push origin v0.3.0
   ```
3. `release.yml` runs the tests, checks that the tag matches `pyproject.toml`,
   publishes to PyPI, and creates the GitHub release with generated notes.
   `terminal-build.yml` builds the macOS and Windows downloads and attaches them
   to the same release.

The production server deploys only when someone runs the **Production deploy to
Render** workflow by hand from the Actions tab.
