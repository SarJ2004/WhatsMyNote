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

## 2. Authentication

When you run `whatsmynote` for the very first time, the system needs to securely identify you so your financial data is completely isolated.

Run the CLI:
```bash
whatsmynote
```

You will see the following prompt:
```text
WhatsMyNote - Supabase Authentication
Do you want to (L)og in, (S)ign up, or (O)Auth [Google/GitHub]? [l/s/o/q] (l): o
Which provider? [google/github] (google): google
Opening browser to authenticate with Google...
```

1. A browser window will automatically pop open.
2. Sign in using your Google or GitHub account.
3. You will see a beautiful **"Access Granted"** success page.
4. You can safely close the tab, and the terminal will say:
   `Successfully authenticated via Google!`

> **Security Note:** The CLI securely stores your session token locally on your machine. You will only ever have to log in once!

## 3. Initial Setup Wizard

Upon your very first successful login, WhatsMyNote will realize your database is empty. It will automatically launch an interactive setup wizard to get your baseline finances configured.

### Setting up your Accounts
First, it will ask you what bank accounts or wallets you want to track:
```text
Let's set up your accounts.
Account Name (e.g., SBI, Cash, HDFC): HDFC
Opening Balance (0.0): 1500
Currency (INR, USD, etc.): USD
```

Next, it will ask you to select a **Default Account**. 
*Why?* If you type *"I bought a coffee for $5"*, the AI will automatically deduct it from your Default Account so you don't have to specify "from HDFC" every single time!

### Setting up your Budgets
Next, it will ask if you want to configure monthly spending limits:
```text
Category Name (e.g., Food, Travel, Rent): Food
Monthly Budget Amount: 500
```
*(You can easily skip this by pressing Enter if you don't want to track budgets).*

## 4. You are ready!

Once the setup wizard finishes, you will see the main chat interface:

```text
╭──────────────────────────────────────────────────╮
│ WhatsMyNote CLI                                  │
│ Type finance messages. Use exit or quit to stop. │
╰──────────────────────────────────────────────────╯
You: 
```

**Try typing your first message!**
> *"I just grabbed a $5 coffee"*
> *"My employer deposited my $5000 salary into HDFC"*
> *"My friend Alex borrowed $50 from me"*

**Built-in Commands:**
- `clear`: Clears the terminal screen.
- `/logout`: Logs you out and clears your session token.
- `exit` or `quit`: Closes the application.
