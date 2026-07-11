# Getting Started

Welcome to **WhatsMyNote**! This guide will help you install the application, log in, and perform the initial setup.

## Installation

WhatsMyNote is distributed via PyPI. You can install it globally using `uv` (recommended for speed) or `pip`.

```bash
# Using uv (Recommended)
uv tool install whatsmynote

# Using pip
pip install whatsmynote
```

## Authentication

When you run `whatsmynote` for the first time, you will be prompted to authenticate. 

1. A browser window will automatically open pointing to Supabase.
2. Sign in using your preferred OAuth provider (e.g., Google or GitHub).
3. Once successful, you will be redirected back to the CLI automatically. 
4. The CLI securely stores your session token locally, meaning you only have to log in once!

## Initial Setup

Upon successful login, WhatsMyNote will detect if you have any existing accounts. If you don't, it will guide you through an interactive setup:

1. **Default Account**: You will be asked to create a default bank account or wallet (e.g., `SBI`, `HDFC`, `Cash`). This acts as the default fallback for all transactions if you do not specify an account name in your messages.
2. **Budgets**: You can optionally set up monthly spending limits for various categories (e.g., Food, Transport, Rent). 

Once completed, you will enter the main chat interface!

## Basic Usage

The CLI operates exactly like a chat window. Type your financial events in natural English, and the AI will parse them and update your database automatically.

**Built-in Commands:**
- `clear`: Clears the terminal screen.
- `exit` or `quit`: Closes the application.
