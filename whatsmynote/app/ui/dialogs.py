"""Small centred dialogs. Each one does one job, shows its own errors in place,
and closes with a result, or None when cancelled with esc."""

import asyncio
import re
import threading
from decimal import Decimal, InvalidOperation

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, OptionList, Static
from textual.widgets.option_list import Option

from whatsmynote.app.config import ModelSettings, check_model_settings
from whatsmynote.app.ui.constants import ACCENT, MUTED

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_AMOUNT = re.compile(r"^-?(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?$")


def parse_amount(text: str) -> int | None:
    """Read a typed amount such as 1,500.50 as minor units. None when unreadable."""
    raw = text.strip().replace(" ", "")
    if not raw:
        return 0
    if not _AMOUNT.match(raw):
        return None
    try:
        return int(Decimal(raw.replace(",", "")) * 100)
    except InvalidOperation:
        return None


class Dialog(ModalScreen):
    """Shared frame: a title, a body, a line for errors, and esc to close."""

    BINDINGS = [Binding("escape", "close", "Cancel", show=False)]
    TITLE_TEXT = ""

    def compose(self) -> ComposeResult:
        with Vertical(classes="dialog") as frame:
            frame.border_title = self.TITLE_TEXT
            yield from self.body()
            yield Label("", classes="dialog-error")
            yield from self.actions()

    def body(self) -> ComposeResult:
        yield from ()

    def actions(self) -> ComposeResult:
        yield from ()

    def action_close(self) -> None:
        self.dismiss(None)

    def show_error(self, sentence: str) -> None:
        label = self.query_one(".dialog-error", Label)
        label.update(sentence)
        label.display = bool(sentence)

    def on_mount(self) -> None:
        self.show_error("")

    @on(Button.Pressed, ".cancel")
    def _cancel(self) -> None:
        self.action_close()


def _buttons(primary: str, *others: tuple[str, str]) -> Horizontal:
    buttons = [Button(primary, variant="primary", classes="submit", compact=True)]
    buttons += [Button(label, classes=cls, compact=True) for label, cls in others]
    return Horizontal(*buttons, classes="dialog-actions")


class SignInMenu(Dialog):
    TITLE_TEXT = "Sign in"
    BINDINGS = [Binding(str(n), f"pick({n})", show=False) for n in range(1, 6)]
    CHOICES = [
        ("email", "Sign in with email and password"),
        ("google", "Continue with Google  (opens your browser)"),
        ("github", "Continue with GitHub  (opens your browser)"),
        ("signup", "Create an account with email"),
        ("reset", "Forgot your password?"),
    ]

    def body(self) -> ComposeResult:
        yield OptionList(
            *[Option(f"{n}  {label}", id=key) for n, (key, label) in enumerate(self.CHOICES, 1)],
            id="sign-in-choices",
        )
        yield Static(Text("↑ ↓ to move, enter to choose, esc to cancel", style=MUTED), classes="dialog-help")

    def action_pick(self, number: int) -> None:
        self.dismiss(self.CHOICES[number - 1][0])

    @on(OptionList.OptionSelected)
    def _chosen(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)


class EmailForm(Dialog):
    """Email and password go only to the sign-in service, never to the engine."""

    def __init__(self, auth, mode: str = "signin", email: str = ""):
        super().__init__()
        self.auth = auth
        self.mode = mode
        self.email = email
        self.TITLE_TEXT = "Create an account" if mode == "signup" else "Sign in with email"

    def body(self) -> ComposeResult:
        yield Label("Email", classes="field-label")
        yield Input(value=self.email, placeholder="you@example.com", id="email")
        yield Label("Password", classes="field-label")
        yield Input(password=True, placeholder="at least 6 characters" if self.mode == "signup" else "",
                    id="password")
        if self.mode == "signup":
            yield Label("Password again", classes="field-label")
            yield Input(password=True, id="password-again")

    def actions(self) -> ComposeResult:
        yield _buttons("Create account" if self.mode == "signup" else "Sign in", ("Cancel", "cancel"))

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#password" if self.email else "#email", Input).focus()

    @on(Input.Submitted)
    def _next(self, event: Input.Submitted) -> None:
        inputs = list(self.query(Input))
        index = inputs.index(event.input)
        if index < len(inputs) - 1:
            inputs[index + 1].focus()
        else:
            self._submit()

    @on(Button.Pressed, ".submit")
    def _submit(self) -> None:
        email = self.query_one("#email", Input).value.strip()
        password = self.query_one("#password", Input).value
        if not _EMAIL.match(email):
            self.show_error("Enter an email address, like you@example.com.")
            self.query_one("#email", Input).focus()
            return
        if not password:
            self.show_error("Enter your password.")
            self.query_one("#password", Input).focus()
            return
        if self.mode == "signup":
            if len(password) < 6:
                self.show_error("Choose a password with at least 6 characters.")
                return
            if password != self.query_one("#password-again", Input).value:
                self.show_error("The two passwords are different. Type them again.")
                self.query_one("#password-again", Input).value = ""
                self.query_one("#password-again", Input).focus()
                return
        self._send(email, password)

    @work(exclusive=True)
    async def _send(self, email: str, password: str) -> None:
        from whatsmynote.app.auth import auth_error_sentence

        submit = self.query_one(".submit", Button)
        submit.disabled = True
        submit.label = "Creating..." if self.mode == "signup" else "Signing in..."
        self.show_error("")
        try:
            if self.mode == "signup":
                user, signed_in = await asyncio.to_thread(self.auth.sign_up, email, password)
                self.dismiss({"user": user, "signed_in": signed_in, "email": email})
            else:
                user = await asyncio.to_thread(self.auth.sign_in, email, password)
                self.dismiss({"user": user, "signed_in": bool(user), "email": email})
        except Exception as error:
            self.show_error(auth_error_sentence(error))
            submit.disabled = False
            submit.label = "Create account" if self.mode == "signup" else "Sign in"
            self.query_one("#password", Input).focus()


class BrowserWait(Dialog):
    """Waits while the person finishes a step in the browser."""

    def __init__(self, title: str, message: str, wait, link: str = ""):
        super().__init__()
        self.TITLE_TEXT = title
        self.message = message
        self.wait = wait
        self.link = link
        self.cancel = threading.Event()

    def body(self) -> ComposeResult:
        yield Static(Text(self.message), classes="dialog-text")
        if self.link:
            yield Static(Text("If the browser did not open, copy this link into it:", style=MUTED),
                         classes="dialog-help")
            yield Static(Text(self.link, style=ACCENT, overflow="fold"), id="link")
        yield Static(Text("Waiting for the browser... esc to cancel", style=MUTED), classes="dialog-help")

    def actions(self) -> ComposeResult:
        if self.link:
            yield _buttons("Copy link", ("Cancel", "cancel"))
        else:
            with Horizontal(classes="dialog-actions"):
                yield Button("Cancel", classes="cancel", compact=True)

    def on_mount(self) -> None:
        super().on_mount()
        self._wait()

    @on(Button.Pressed, ".submit")
    def _copy(self) -> None:
        self.app.copy_to_clipboard(self.link)
        self.app.notify("Link copied.")

    def action_close(self) -> None:
        self.cancel.set()
        self.dismiss(None)

    @work(exclusive=True)
    async def _wait(self) -> None:
        from whatsmynote.app.auth import auth_error_sentence

        try:
            user = await asyncio.to_thread(self.wait, self.cancel)
        except Exception as error:
            if not self.cancel.is_set():
                self.dismiss({"error": auth_error_sentence(error)})
            return
        if not self.cancel.is_set():
            self.dismiss({"user": user})

    def on_unmount(self) -> None:
        self.cancel.set()


class ResetForm(Dialog):
    TITLE_TEXT = "Reset your password"

    def __init__(self, auth, email: str = ""):
        super().__init__()
        self.auth = auth
        self.email = email

    def body(self) -> ComposeResult:
        yield Static(Text("We will email you a link. Open it on this computer.", style=MUTED),
                     classes="dialog-help")
        yield Label("Email", classes="field-label")
        yield Input(value=self.email, placeholder="you@example.com", id="email")

    def actions(self) -> ComposeResult:
        yield _buttons("Send link", ("Cancel", "cancel"))

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#email", Input).focus()

    @on(Input.Submitted)
    @on(Button.Pressed, ".submit")
    def _submit(self) -> None:
        email = self.query_one("#email", Input).value.strip()
        if not _EMAIL.match(email):
            self.show_error("Enter an email address, like you@example.com.")
            return
        self._send(email)

    @work(exclusive=True)
    async def _send(self, email: str) -> None:
        from whatsmynote.app.auth import auth_error_sentence

        submit = self.query_one(".submit", Button)
        submit.disabled = True
        try:
            await asyncio.to_thread(self.auth.send_reset, email)
        except Exception as error:
            self.show_error(auth_error_sentence(error))
            submit.disabled = False
            return
        self.dismiss(email)


class NewPasswordForm(Dialog):
    TITLE_TEXT = "Choose a new password"

    def __init__(self, auth):
        super().__init__()
        self.auth = auth

    def body(self) -> ComposeResult:
        yield Label("New password", classes="field-label")
        yield Input(password=True, placeholder="at least 6 characters", id="password")
        yield Label("New password again", classes="field-label")
        yield Input(password=True, id="password-again")

    def actions(self) -> ComposeResult:
        yield _buttons("Save password", ("Cancel", "cancel"))

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#password", Input).focus()

    @on(Input.Submitted, "#password")
    def _next(self) -> None:
        self.query_one("#password-again", Input).focus()

    @on(Input.Submitted, "#password-again")
    @on(Button.Pressed, ".submit")
    def _submit(self) -> None:
        password = self.query_one("#password", Input).value
        if len(password) < 6:
            self.show_error("Choose a password with at least 6 characters.")
            return
        if password != self.query_one("#password-again", Input).value:
            self.show_error("The two passwords are different. Type them again.")
            return
        self._send(password)

    @work(exclusive=True)
    async def _send(self, password: str) -> None:
        from whatsmynote.app.auth import auth_error_sentence

        try:
            await asyncio.to_thread(self.auth.set_password, password)
        except Exception as error:
            self.show_error(auth_error_sentence(error))
            return
        self.dismiss(True)


class KeyForm(Dialog):
    """Set, change or remove the user's own model key. It is kept in a private
    file on this computer and sent with each message, never stored by the server."""

    TITLE_TEXT = "Your model key"

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.current: ModelSettings = store.load()

    def body(self) -> ComposeResult:
        yield Static(Text(
            "Use your own OpenAI-compatible key. It stays on this computer and is "
            "sent with each message.", style=MUTED), classes="dialog-help")
        yield Label("Model key", classes="field-label")
        saved = f"saved key {self.current.masked()}, leave blank to keep it" if self.current.key else "sk-..."
        yield Input(password=True, placeholder=saved, id="key")
        yield Label("Base URL  (optional)", classes="field-label")
        yield Input(value=self.current.base_url, placeholder="https://api.openai.com/v1", id="base-url")
        yield Label("Model name  (optional)", classes="field-label")
        yield Input(value=self.current.name, placeholder="gpt-4o-mini", id="model-name")

    def actions(self) -> ComposeResult:
        others = [("Remove key", "remove")] if self.current.key else []
        yield _buttons("Save", *others, ("Cancel", "cancel"))

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#key", Input).focus()

    @on(Input.Submitted)
    def _next(self, event: Input.Submitted) -> None:
        inputs = list(self.query(Input))
        index = inputs.index(event.input)
        if index < len(inputs) - 1:
            inputs[index + 1].focus()
        else:
            self._save()

    @on(Button.Pressed, ".submit")
    def _save(self) -> None:
        key = self.query_one("#key", Input).value.strip() or self.current.key
        base_url = self.query_one("#base-url", Input).value.strip().rstrip("/")
        name = self.query_one("#model-name", Input).value.strip()
        problem = check_model_settings(key, base_url, name)
        if problem:
            self.show_error(problem)
            return
        self.store.save(ModelSettings(key=key, base_url=base_url, name=name))
        self.dismiss("saved")

    @on(Button.Pressed, ".remove")
    def _remove(self) -> None:
        self.store.clear()
        self.dismiss("removed")


class AccountForm(Dialog):
    """Adds an account through the engine. The terminal only reads the amount."""

    def __init__(self, engine, first: bool = False):
        super().__init__()
        self.engine = engine
        self.first = first
        self.TITLE_TEXT = "Set up your first account" if first else "Add an account"

    def body(self) -> ComposeResult:
        if self.first:
            yield Static(Text(
                "Money is recorded against an account. Start with the one you use most. "
                "You can add more later with /account.", style=MUTED), classes="dialog-help")
        yield Label("Name", classes="field-label")
        yield Input(value="Cash" if self.first else "", placeholder="Cash, HDFC, Wallet", id="name")
        with Horizontal(classes="field-row"):
            with Vertical(classes="field-small"):
                yield Label("Currency", classes="field-label")
                yield Input(value="INR", placeholder="INR", max_length=3, id="currency")
            with Vertical(classes="field-wide"):
                yield Label("Balance today", classes="field-label")
                yield Input(value="0", placeholder="1,500.00", id="opening")

    def actions(self) -> ComposeResult:
        yield _buttons("Add account", ("Not now" if self.first else "Cancel", "cancel"))

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#name", Input).focus()

    @on(Input.Submitted)
    def _next(self, event: Input.Submitted) -> None:
        inputs = list(self.query(Input))
        index = inputs.index(event.input)
        if index < len(inputs) - 1:
            inputs[index + 1].focus()
        else:
            self._submit()

    @on(Button.Pressed, ".submit")
    def _submit(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        currency = self.query_one("#currency", Input).value.strip().upper()
        opening = parse_amount(self.query_one("#opening", Input).value)
        if not name:
            self.show_error("Give the account a name, like Cash.")
            return
        if not re.fullmatch(r"[A-Z]{3}", currency):
            self.show_error("Currency is a three-letter code, like INR or USD.")
            return
        if opening is None:
            self.show_error("Write the balance as a number, like 1500 or 1,500.50.")
            return
        self._send(name, currency, opening)

    @work(exclusive=True)
    async def _send(self, name: str, currency: str, opening: int) -> None:
        submit = self.query_one(".submit", Button)
        submit.disabled = True
        result = await asyncio.to_thread(self.engine.open_account, name, currency, opening)
        if result.error:
            self.show_error(result.error)
            submit.disabled = False
            return
        self.dismiss(name)
