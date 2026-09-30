"""Turns results into Rich renderables. No finance decisions live here, and
nothing from the server is read as markup."""

from rich import box
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from whatsmynote.app.ui.constants import ACCENT, BAD, COMMANDS, EXAMPLES, GOOD, INK, MUTED


def display_name(user) -> str:
    metadata = getattr(user, "user_metadata", None) or {}
    full_name = metadata.get("full_name") or metadata.get("name") or ""
    if full_name:
        return full_name.split(" ")[0]
    email = getattr(user, "email", "") or ""
    return email.split("@")[0] if email else "you"


def format_minor(value, currency: str | None = None) -> str:
    """Show an integer minor-unit amount, for example 150050 as 1,500.50.
    This does not convert currencies."""
    if isinstance(value, bool) or not isinstance(value, int):
        return str(value)
    sign = "-" if value < 0 else ""
    whole, fraction = divmod(abs(value), 100)
    shown = f"{sign}{whole:,}.{fraction:02d}"
    return f"{shown} {currency}" if currency else shown


def _prefixed(glyph: str, glyph_style: str, message: str) -> Table:
    """A line with a marker in front. Wrapped text lines up under the first word."""
    grid = Table.grid(padding=(0, 1, 0, 0))
    grid.add_column(no_wrap=True, width=1)
    grid.add_column()
    grid.add_row(Text(glyph, style=glyph_style), Text(message, style=INK))
    return grid


def you(message: str) -> Table:
    return _prefixed("›", f"bold {ACCENT}", message)


def note(message: str) -> Text:
    return Text(message, style=MUTED)


def success(message: str) -> Table:
    return _prefixed("✓", f"bold {GOOD}", message)


def problem(message: str) -> Table:
    return _prefixed("✗", f"bold {BAD}", message)


def balance_line(balance: int) -> Text:
    text = Text()
    text.append("Balance  ", style=MUTED)
    text.append(format_minor(balance), style=f"bold {INK}")
    return text


def observation_line(kind: str, category: str, detail: str) -> Table:
    label = category or kind
    warn = kind.lower() in {"warning", "warn", "alert", "limit", "budget"}
    colour = ACCENT if warn else MUTED
    text = Text()
    if label:
        text.append(f"{label}  ", style=f"bold {colour}")
    text.append(detail, style=INK if warn else MUTED)
    grid = Table.grid(padding=(0, 1, 0, 0))
    grid.add_column(no_wrap=True, width=1)
    grid.add_column()
    grid.add_row(Text("●", style=colour), text)
    return grid


def confirmation_card(summary: str) -> Panel:
    body = Text(summary, style=INK)
    body.append("\n\n")
    body.append("y", style=f"bold {ACCENT}")
    body.append(" confirm    ", style=MUTED)
    body.append("n", style=f"bold {ACCENT}")
    body.append(" cancel    ", style=MUTED)
    body.append("expires in 10 minutes", style=MUTED)
    return Panel(
        body, title=Text(" Confirm this change ", style=f"bold {ACCENT}"),
        title_align="left", box=box.ROUNDED, border_style=ACCENT, padding=(0, 1),
    )


def result_renderables(result) -> list[RenderableType]:
    """What one answer from the engine looks like, in reading order."""
    if result.error:
        return [problem(result.error)]
    parts: list[RenderableType] = []
    if result.reply:
        parts.append(Text(result.reply, style=INK))
    elif result.balance is not None:
        parts.append(balance_line(result.balance))
    for item in result.observations:
        parts.append(observation_line(item.kind, item.category, item.detail))
    if result.confirmation:
        parts.append(confirmation_card(result.confirmation.summary))
    if not parts:
        parts.append(note("Done. The server had nothing else to add."))
    return parts


def help_table() -> Table:
    table = Table(box=None, show_header=False, padding=(0, 2, 0, 0), expand=False)
    table.add_column(style=f"bold {ACCENT}", no_wrap=True)
    table.add_column(style=INK)
    for command, meaning in COMMANDS:
        table.add_row(command, meaning)
    table.add_row("", "")
    table.add_row(Text("↑ ↓", style=f"bold {ACCENT}"), Text("Bring back what you typed before", style=INK))
    table.add_row(Text("esc", style=f"bold {ACCENT}"), Text("Cancel what is being asked", style=INK))
    return table


def balances_table(rows: list) -> RenderableType:
    if not rows:
        return note("No accounts yet. Add one with /account.")
    table = Table(box=None, header_style=f"bold {MUTED}", padding=(0, 3, 0, 0), expand=False)
    table.add_column("Account", style=INK)
    table.add_column("Balance", justify="right", style=f"bold {INK}", no_wrap=True)
    for row in rows:
        amount = row.get("current_balance", row.get("balance"))
        currency = row.get("currency") or None
        table.add_row(str(row.get("name") or "Account"), format_minor(amount, currency))
    return table


def _step(done: bool, number: str, title: str, command: str, detail: str):
    marker = Text("✓" if done else number, style=f"bold {GOOD if done else ACCENT}")
    return (
        marker,
        Text(title, style=INK if not done else MUTED),
        Text(command, style=f"bold {ACCENT}" if command else ""),
        Text(detail, style=MUTED),
    )


def welcome(signed_in: bool, name: str = "", key_hint: str = "", checking: bool = False) -> Group:
    """The empty state. It says what to type next, in order."""
    greeting = f"Welcome back, {name}." if signed_in and name else "Welcome."
    title = Text(greeting, style=f"bold {INK}")
    tagline = note("Keep track of money by writing it down, the way you would say it.")

    steps = Table(box=None, show_header=False, padding=(0, 2, 0, 0), expand=False)
    steps.add_column(no_wrap=True, width=1)
    steps.add_column(no_wrap=True, min_width=20)
    steps.add_column(no_wrap=True)
    steps.add_column()
    if checking:
        steps.add_row(*_step(False, "1", "Sign in", "", "checking for a saved sign-in..."))
    elif signed_in:
        steps.add_row(*_step(True, "1", "Signed in", "/logout", "to switch accounts"))
    else:
        steps.add_row(*_step(False, "1", "Sign in", "/login", "email, Google or GitHub"))
    if key_hint:
        steps.add_row(*_step(True, "2", f"Model key {key_hint}", "/key", "to change or remove"))
    else:
        steps.add_row(*_step(False, "2", "Add a model key", "/key", "optional, stays on this computer"))
    steps.add_row(*_step(False, "3", "Write what happened", "", ""))
    for example in EXAMPLES:
        steps.add_row("", Text(example, style=ACCENT), "", "")

    footer = Text()
    footer.append("/help", style=f"bold {ACCENT}")
    footer.append(" lists every command.", style=MUTED)
    return Group(title, tagline, Text(""), steps, Text(""), footer)
