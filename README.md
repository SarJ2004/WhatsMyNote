<div align="center">
<img src="https://raw.githubusercontent.com/SarJ2004/WhatsMyNote/main/docs/assets/logo.png" alt="WhatsMyNote logo" width="100" height="100">
<h3>WhatsMyNote</h3>
<p>
Track your money by writing what happened, in plain words.<br/>
One open-source engine behind a website, a terminal app, and MCP tools.
</p>

[![PyPI Version](https://img.shields.io/pypi/v/whatsmynote.svg?color=blue)](https://pypi.org/project/whatsmynote/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/whatsmynote.svg)](https://pypi.org/project/whatsmynote/)
</div>

---

## Contents

- [What it is](#what-it-is)
- [Bring your own model key](#bring-your-own-model-key)
- [Use the website](#use-the-website)
- [Install the terminal app](#install-the-terminal-app)
- [MCP tools](#mcp-tools)
- [Self-host it](#self-host-it)
- [Contributing](#contributing)
- [License](#license)

---

## What it is

WhatsMyNote is a personal expense tracker you talk to. Type what happened:

> spent 400 on dinner from HDFC
> John borrowed 50
> how much did I spend on food this month?

and it books the expense against the right account, tracks who owes whom, and answers questions about your spending.

A few things it does on purpose:

- **Money is exact.** Amounts are stored as whole minor units (paise, cents). A booking in another currency keeps the original amount and currency next to the converted one, using [Frankfurter](https://frankfurter.dev) reference rates. If no rate is available it tells you instead of guessing.
- **Your rows are yours.** Row-level security in the database, not application code, keeps one user from reading or writing another user's records.
- **The model never touches your data directly.** Plain code parses the message and builds every query. A language model is only asked what you meant and to phrase the answer, and it never writes SQL or sees the schema.
- **Nothing destructive happens silently.** A delete, or an edit whose target is ambiguous, comes back as a confirmation request. Nothing changes until you confirm it, and the confirmation expires after ten minutes.

There are three ways in, all talking to the same engine:

| Surface | What it is |
|---|---|
| Website | A single page: balances, a spending-by-category chart, a searchable record table, and the chat. |
| Terminal | `whatsmynote`, a terminal app for macOS, Windows and Linux. |
| MCP | Tools an AI assistant can call to log and read your books on your behalf. |

## Bring your own model key

WhatsMyNote does not ship or pay for a language model. You bring a key for any OpenAI-compatible endpoint (OpenAI, Groq, OpenRouter, a local server, and so on).

- The website and the terminal ask for your key, and optionally a base URL and model name, and send them with each request.
- The server uses the key for that one request only. It is never stored server-side, never logged, and never echoed back in a response or an error.
- The website keeps the key in your browser's local storage. The terminal keeps it in its own config file in your user data directory.

If you self-host, clients talk to your server with these request headers:

| Header | Meaning |
|---|---|
| `Authorization: Bearer <token>` | Your Supabase access token. Required. |
| `X-Model-Key` | Your model key. |
| `X-Model-Base-URL` | Base URL of an OpenAI-compatible API. |
| `X-Model-Name` | The model to call. |

## Use the website

The engine serves the website at the root of the server (`/`). The hosted instance runs at **<https://whatsmynote-staging.onrender.com>** while the rebuilt engine is in staging.

1. Open the site and create an account with your email and a password.
2. Enter your model key.
3. On first visit, set up an account (for example `HDFC`, currency `INR`, opening balance) before the chat will book anything.
4. Start typing what you spent.

The hosted instance runs on a free tier, so the first request after a quiet spell can take up to a minute while the server wakes up.

## Install the terminal app

### With Python (macOS, Windows, Linux)

You need Python 3.11 or newer.

```bash
# Recommended: uv installs it as an isolated tool
uv tool install whatsmynote

# Or with pip
pip install whatsmynote
```

Then run:

```bash
whatsmynote
```

To upgrade later: `uv tool upgrade whatsmynote` or `pip install --upgrade whatsmynote`.

### Without Python (download)

Every version tag also publishes one-file builds on the [releases page](https://github.com/SarJ2004/WhatsMyNote/releases/latest).

| Platform | Download |
|---|---|
| macOS (Apple silicon) | [`whatsmynote-macos`](https://github.com/SarJ2004/WhatsMyNote/releases/latest/download/whatsmynote-macos) |
| Windows | [`whatsmynote-windows.exe`](https://github.com/SarJ2004/WhatsMyNote/releases/latest/download/whatsmynote-windows.exe) |

The builds are not code-signed, so your operating system will warn you the first time:

- **macOS**: make the file executable and clear the download quarantine, then run it from a terminal.
  ```bash
  chmod +x whatsmynote-macos
  xattr -d com.apple.quarantine whatsmynote-macos
  ./whatsmynote-macos
  ```
- **Windows**: run `whatsmynote-windows.exe` from PowerShell or Windows Terminal. If SmartScreen appears, choose **More info**, then **Run anyway**.

Intel Macs and Linux: use the Python install above.

### First run

The terminal works in any terminal at least 80 columns wide, including macOS Terminal and Windows Terminal. The first screen lists these steps:

1. Type `/login` and pick email and password, Google, or GitHub. Creating an account and resetting a password are in the same menu. The password goes only to the sign-in service, and the session is stored locally, so you sign in once.
2. If you have no account yet, the terminal asks for its name, currency and balance today.
3. Enter your model key when asked, with an optional base URL and model name. Change or remove it any time with `/key`.
4. Type what happened, in plain words, such as `spent 400 on dinner`. When a change needs your say-so, a card asks you to confirm: type `y` to confirm or `n` to cancel.

| Command or key | What it does |
|---|---|
| `/login`, `/logout` | Sign in or create an account; sign out of this computer. |
| `/key` | Set, change or remove your model key. |
| `/account` | Add an account, like Cash or a bank. |
| `/balances` | Show every account and its balance. |
| `/clear`, `/help`, `/quit` | Clear the conversation, list every command, close the app. |
| Up and Down | Bring back what you typed before. |
| Esc | Cancel what is being asked. |
| Ctrl+C | Copy selected text, or quit when nothing is selected. Ctrl+Q always quits. |

## MCP tools

The engine also exposes its bookkeeping as MCP tools, in [`mcp_server/server.py`](mcp_server/server.py):

| Tool | What it does |
|---|---|
| `log_expense` | Book an expense, from structured fields or a plain sentence. |
| `log_income` | Book income into an account. |
| `transfer` | Move money between two of your accounts. |
| `balances` | Read your account balances. |
| `spending` | Spending by category over a date range (defaults to this month). |
| `ask` | Book an expense from one plain sentence and return your balances. |

Every call carries your Supabase access token, and the engine takes your identity from that token. No tool accepts a user id, so an assistant cannot read someone else's books even if it tries.

## Self-host it

You need a [Supabase](https://supabase.com) project (the free tier is enough), a host that can run a Python web service (for example [Render](https://render.com), Fly.io, Railway, or your own machine), and Python 3.11+ with [uv](https://docs.astral.sh/uv/).

### 1. Create the database

1. Create a Supabase project.
2. Under **Authentication > Sign In / Providers**, make sure **Email** is enabled. Turn off **Confirm email** if you do not want to set up email delivery.
3. Apply the schema. Every file in [`supabase/migrations/`](supabase/migrations) is plain SQL, applied in filename order. Either paste each file into the Supabase **SQL Editor** and run it, or use `psql`:
   ```bash
   for f in supabase/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
   ```
   Warning: `0001_isolation.sql` drops and recreates the WhatsMyNote tables. Run it only on a new, empty project.

### 2. Configure the environment

The engine reads exactly three variables. [`.env.sample`](.env.sample) lists them:

| Variable | Where to find it |
|---|---|
| `SUPABASE_URL` | Project Settings > Data API > Project URL, for example `https://abcd1234.supabase.co`. |
| `SUPABASE_KEY` | Project Settings > API Keys: the publishable (anon) key. The engine only uses it to verify sign-in tokens. |
| `DATABASE_URL` | Connect > Connection string: the **direct connection** or **session pooler** string (port 5432), for the `postgres` user. The engine switches to the restricted `authenticated` role for every request, so this user must be allowed to do that. |

There is no model key in the server environment. Keys come from each user, per request.

### 3. Run the engine

Locally:

```bash
git clone https://github.com/SarJ2004/WhatsMyNote.git
cd WhatsMyNote
cp .env.sample .env        # then fill in the three values
uv sync
uv run --env-file .env uvicorn --factory engine.api:create_live_app --reload
```

Open <http://127.0.0.1:8000/health>; it should answer `{"status":"ok"}`.

On Render (or any host), create a Python web service from your fork:

| Setting | Value |
|---|---|
| Build command | `pip install uv && uv sync --frozen` |
| Start command | `.venv/bin/uvicorn --factory engine.api:create_live_app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Environment | `SUPABASE_URL`, `SUPABASE_KEY`, `DATABASE_URL` |

### 4. Point the clients at your server

The website and the terminal have the hosted server's address built in. For your own server, change it in two places:

- **Website**: in [`web/index.html`](web/index.html), set `API` to your server's URL, and `SUPABASE_URL` and `SUPABASE_KEY` to your project's values. The engine serves this file at `/`, so redeploy after editing.
- **Terminal**: in [`whatsmynote/app/config.py`](whatsmynote/app/config.py), set `API_URL`, `SUPABASE_URL` and `SUPABASE_KEY`, then run it from your clone with `uv run whatsmynote`. To try another engine without editing, set `WMN_API_URL`, for example `WMN_API_URL=http://127.0.0.1:8000 uv run whatsmynote`.

### Deploying from GitHub Actions

If you keep the workflows in [`.github/workflows`](.github/workflows):

- `tests.yml` runs the test suite on every pull request.
- `render-deploy-staging.yml` deploys a staging service on every push to `deploy/backend-render`. It needs the secrets `RENDER_API_KEY` and `STAGING_RENDER_SERVICE_ID`.
- `render-deploy.yml` deploys production only when you run it by hand from the Actions tab. It needs `RENDER_API_KEY` and `RENDER_SERVICE_ID`.
- `release.yml` publishes to PyPI, and `terminal-build.yml` attaches the macOS and Windows downloads, only when a version tag is pushed. See [CONTRIBUTING.md](CONTRIBUTING.md#releasing).

## Contributing

Bug reports and pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) explains how to set up a checkout and run the tests locally.

## License

MIT. See [LICENSE](LICENSE).
