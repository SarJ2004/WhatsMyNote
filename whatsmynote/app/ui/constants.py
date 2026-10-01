"""Shared copy and colours. The colours match the web site's dark palette."""

PAPER = "#16130f"
CARD = "#221e19"
LINE = "#3a342c"
INK = "#f5f0e8"
MUTED = "#b5ada3"
ACCENT = "#fdba74"
GOOD = "#bef264"
BAD = "#fda4af"

COMMANDS = [
    ("/login", "Sign in or create an account"),
    ("/key", "Set, change or remove your model key"),
    ("/account", "Add an account, like Cash or a bank"),
    ("/balances", "Show every account and its balance"),
    ("/clear", "Clear the conversation"),
    ("/logout", "Sign out of this computer"),
    ("/help", "Show this list"),
    ("/quit", "Close WhatsMyNote"),
]

# Older names people may still type.
ALIASES = {
    "/signin": "/login",
    "/signup": "/login",
    "/config": "/key",
    "/balance": "/balances",
    "/exit": "/quit",
    "/signout": "/logout",
}

EXAMPLES = [
    "spent 400 on dinner",
    "got 50000 salary",
    "lent 500 to Sam",
]

YES = {"y", "yes", "confirm", "ok"}
NO = {"n", "no", "cancel", "q"}
