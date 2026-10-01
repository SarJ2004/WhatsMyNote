import difflib

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Label

from whatsmynote.app.ui.constants import ACCENT, ALIASES, COMMANDS, MUTED, NO, YES
from whatsmynote.app.ui.mixins.auth import AuthMixin
from whatsmynote.app.ui.mixins.chat import ChatMixin
from whatsmynote.app.ui.mixins.onboarding import OnboardingMixin
from whatsmynote.app.ui.present import display_name, help_table, note, problem, welcome, you
from whatsmynote.app.ui.widgets import HintBar, HistoryInput, Message, TopBar

_COMMAND_NAMES = [command for command, _ in COMMANDS]


class MainScreen(AuthMixin, OnboardingMixin, ChatMixin, Screen):
    def __init__(self):
        super().__init__()
        self.user = None
        self.checking = True
        self.jobs = 0
        self.chatting = False
        self.pending = None
        self.pending_at = 0.0

    def compose(self) -> ComposeResult:
        yield TopBar()
        with VerticalScroll(id="log"):
            yield Message(self._welcome(), "welcome")
        yield HistoryInput(id="main-input")
        yield HintBar()

    def on_mount(self) -> None:
        self.refresh_status()
        self.query_one("#main-input", Input).focus()
        self.restore_session()

    # --- what the screen shows -------------------------------------------

    def _welcome(self):
        key = self.app.keys.load()
        return welcome(
            signed_in=self.user is not None,
            name=display_name(self.user) if self.user else "",
            key_hint=key.masked(),
            checking=self.checking,
        )

    def say(self, *renderables, kind: str = "reply") -> None:
        log = self.query_one("#log", VerticalScroll)
        for renderable in renderables:
            log.mount(Message(renderable, kind))
        log.scroll_end(animate=False)

    def refresh_status(self) -> None:
        """Bring the top bar, the welcome, the placeholder and the hints up to date."""
        key = self.app.keys.load()
        who = self.query_one("#who", Label)
        if self.checking:
            who.update(Text("checking sign-in...", style=MUTED))
        elif self.user:
            status = Text(display_name(self.user), style=ACCENT)
            if key.key:
                status.append("  ·  model key " + key.masked(), style=MUTED)
            else:
                status.append("  ·  no model key  ·  /key", style=MUTED)
            who.update(status)
        else:
            who.update(Text("not signed in  ·  /login", style=MUTED))

        for message in self.query(".welcome"):
            message.update(self._welcome())

        inp = self.query_one("#main-input", Input)
        if self.pending:
            inp.placeholder = "Type y to confirm or n to cancel"
        elif self.checking:
            inp.placeholder = "One moment..."
        elif not self.user:
            inp.placeholder = "Type /login to sign in, or /help"
        else:
            inp.placeholder = "Write what happened, like: spent 400 on dinner"

        hints = Text(style=MUTED)
        pairs = (
            [("y", "confirm"), ("n", "cancel")] if self.pending
            else [("enter", "send"), ("↑", "history"), ("/help", "commands"), ("ctrl+c", "quit")]
        )
        for index, (key_name, meaning) in enumerate(pairs):
            if index:
                hints.append("   ")
            hints.append(key_name, style=f"bold {ACCENT}")
            hints.append(f" {meaning}")
        self.query_one("#hint-left", Label).update(hints)

    def set_busy(self, busy: bool) -> None:
        """Count the requests in flight; the spinner shows while any is."""
        self.jobs = max(0, self.jobs + (1 if busy else -1))
        self.query_one(HintBar).working(self.jobs > 0)

    # --- input ------------------------------------------------------------

    @on(Input.Submitted, "#main-input")
    def submitted(self, event: Input.Submitted) -> None:
        line = event.value.strip()
        inp = self.query_one("#main-input", HistoryInput)
        inp.value = ""
        if not line:
            return
        if self.pending:
            self.answer_pending(line)
            return
        inp.remember(line)
        if line.startswith("/"):
            self.run_command(line)
            return
        self.say(you(line), kind="you")
        if self.checking:
            self.say(note("Still checking your sign-in. Send it again in a moment."))
        elif not self.user:
            self.say(problem("Sign in first so this can be saved. Type /login."))
            self.say(note("Press ↑ after signing in to bring this line back."))
        elif self.chatting:
            self.say(note("Still working on your last message. Send this one when it is done."))
        else:
            self.send_message(line)

    def answer_pending(self, line: str) -> None:
        answer = line.lower()
        self.say(you(line), kind="you")
        if answer in YES:
            self.confirm_pending()
        elif answer in NO:
            self.cancel_pending()
        else:
            self.say(note("Type y to save this change, or n to leave it."))

    def action_cancel_pending(self) -> None:
        if self.pending:
            self.say(you("n"), kind="you")
            self.cancel_pending()

    def run_command(self, line: str) -> None:
        command = line.split()[0].lower()
        command = ALIASES.get(command, command)
        self.say(you(line), kind="you")
        handlers = {
            "/login": self.login_flow,
            "/logout": self.logout_flow,
            "/key": self.key_flow,
            "/account": self.account_flow,
            "/balances": self.show_balances,
            "/clear": self.clear_log,
            "/help": self.show_help,
            "/quit": self.app.exit,
        }
        handler = handlers.get(command)
        if handler is None:
            guess = difflib.get_close_matches(command, _COMMAND_NAMES, n=1)
            hint = f" Did you mean {guess[0]}?" if guess else ""
            self.say(problem(f"There is no {command} command.{hint} Type /help to see them all."))
            return
        if command in {"/login", "/logout"} and self.checking:
            self.say(note("Still checking for a saved sign-in. Try again in a moment."))
            return
        needs_sign_in = {"/account", "/balances"}
        if command in needs_sign_in and not self.user:
            self.say(problem("Sign in first. Type /login."))
            return
        handler()

    def show_help(self) -> None:
        self.say(help_table(), kind="card")

    def clear_log(self) -> None:
        log = self.query_one("#log", VerticalScroll)
        log.remove_children()
        log.mount(Message(self._welcome(), "welcome"))

    # --- keys -------------------------------------------------------------

    @work(exclusive=True, group="dialog")
    async def key_flow(self) -> None:
        await self.edit_key()

    async def edit_key(self, first: bool = False) -> None:
        from whatsmynote.app.ui.dialogs import KeyForm
        from whatsmynote.app.ui.present import success

        outcome = await self.app.push_screen_wait(KeyForm(self.app.keys, first=first))
        if outcome == "saved":
            self.say(success(f"Model key {self.app.keys.load().masked()} saved on this computer. "
                             "It goes with each message you send."))
        elif outcome == "removed":
            self.say(success("Model key removed from this computer."))
        elif first:
            self.say(note("No model key yet. Clear bookings work without one; add it with /key "
                          "for questions and advice."))
        else:
            self.say(note("Model key unchanged."))
        self.refresh_status()
