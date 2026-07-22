# Getting Started

Welcome to **WhatsMyNote**! This guide will walk you through the absolute easiest way to get the CLI installed, authenticated, and configured for your first financial message.

## 1. Installation

WhatsMyNote is distributed securely via PyPI.

```bash
# We highly recommend using uv for lightning-fast installation!
uv tool install whatsmynote

# Or standard pip:
pip install whatsmynote
```

## 2. The Minimalist TUI & Authentication

WhatsMyNote runs entirely inside a sleek, responsive terminal interface powered by Textual.

Run the CLI:
```bash
whatsmynote
```

When you first launch the app, you'll be greeted by the IDLE screen. Since this is your first time, you need to log in to isolate your financial data securely.

**Type the login command:**
```text
> /login
```

The CLI will dynamically prompt you inline:
`Do you want to (L)og in, (S)ign up, (F)orgot Password, or (O)Auth [Google/GitHub]?`

1. **OAuth:** If you choose `o`, the CLI will pop open your browser. Sign in using Google or GitHub. Once the "Access Granted" page appears, safely close the tab. The CLI will automatically intercept the token in the background and log you in!
2. **Email:** If you choose `s`, you can sign up with an email and password directly within the terminal.

> **Security Note:** The CLI securely stores your session token locally on your machine. You will only ever have to log in once!

## 3. Initial Setup Wizard

Upon your very first successful login, the interface will detect that your database is empty. It will seamlessly transition into an interactive onboarding wizard.

### Setting up your Accounts
First, it will ask you what bank accounts or wallets you want to track:
```text
Let's set up your accounts.
Account Name (e.g., SBI, Cash, HDFC) [default: Cash]: HDFC
Opening Balance (0.0): 1500
Currency (INR, USD, etc.) [default: USD]: USD
```

Next, it will ask you to select a **Default Account**. 
*Why?* If you type *"I bought a coffee for $5"*, the AI will automatically deduct it from your Default Account so you don't have to specify "from HDFC" every single time!

### Setting up your Budgets
Next, it will ask if you want to configure monthly spending limits:
```text
Category Name (e.g., Food, Travel, Rent): Food
Monthly Budget Amount: 500
```
*(You can easily skip any prompt by hitting `Enter` to use the default value).*

## 4. You are ready!

Once the setup wizard finishes, your name will appear in the top-right header, and you can begin chatting.

**Try typing your first message:**
> *"I just grabbed a $5 coffee"*
> *"My employer deposited my $5000 salary into HDFC"*
> *"My friend Alex borrowed $50 from me"*

**Global Commands & Hotkeys:**
- `/login`, `/signup`: Authenticate your session.
- `/logout`: Securely log out and wipe your local session token.
- `/config`: Set or update your `GROQ_API_KEY`.
- `/clear`: Clear the chat log.
- `Ctrl+C` or `Ctrl+Q`: Force quit the application instantly.
- `Esc`: Cancel any active flow (e.g., back out of a deletion confirmation).
- `Up/Down Arrows`: Cycle through your previously typed commands.

**Fuzzy Search Modals:**
If you ever want to update or delete a record (e.g. *"Delete my recent lunch expense"*), the UI will pop up a floating modal table. You can use your keyboard to fuzzy search, select multiple rows with `Space`, or hit `Enter` to confirm your action!
