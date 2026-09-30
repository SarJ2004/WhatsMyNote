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

## 2. Sign in

WhatsMyNote runs inside your terminal, on macOS Terminal, Windows Terminal, or any terminal at least 80 columns wide.

```bash
whatsmynote
```

The first screen lists three steps. Type `/login` and pick how to sign in:

1. **Email and password.** Type them into the form. The password goes only to the sign-in service, never to the WhatsMyNote server.
2. **Google or GitHub.** Your browser opens. Sign in there, then come back to the terminal. If the browser does not open, the dialog shows a link you can copy.
3. **Create an account** or **Forgot your password?** work from the same menu.

Your session is saved on this computer, so you sign in once.

## 3. Add your model key (optional)

Type `/key` to use your own OpenAI-compatible key. You can also set a base URL and a model name. The key is kept in a private file on this computer and sent with each message. The server never stores it. Open `/key` again to change or remove it.

## 4. Your first account

After your first sign-in, WhatsMyNote asks for an account to record money against, such as Cash or a bank, and its balance today. Add more any time with `/account`.

## 5. Write what happened

```text
spent 400 on dinner
got 50000 salary
lent 500 to Sam
```

When a change needs your say-so, such as deleting a record, a card asks you to confirm. Type `y` to confirm or `n` to cancel.

**Commands and keys:**
- `/login`: Sign in or create an account.
- `/key`: Set, change or remove your model key.
- `/account`: Add an account.
- `/balances`: Show every account and its balance.
- `/clear`: Clear the conversation.
- `/logout`: Sign out of this computer.
- `/help`: List every command.
- `Up/Down`: Bring back what you typed before.
- `Esc`: Cancel what is being asked.
- `Ctrl+C`: Copy selected text, or quit when nothing is selected. `Ctrl+Q` always quits.
