import shutil
import subprocess
import sys

from textual.app import App
from textual.binding import Binding
from textual.theme import Theme

from whatsmynote.app.ui.constants import ACCENT, BAD, CARD, GOOD, INK, MUTED, PAPER
from whatsmynote.app.ui.screens import MainScreen
from whatsmynote.app.ui.styles import CSS as STYLES

THEME = Theme(
    name="whatsmynote",
    primary=ACCENT,
    secondary=MUTED,
    accent=ACCENT,
    foreground=INK,
    background=PAPER,
    surface=CARD,
    panel=CARD,
    success=GOOD,
    warning=ACCENT,
    error=BAD,
    dark=True,
)


class WhatsMyNoteApp(App):
    TITLE = "WhatsMyNote"
    CSS = STYLES
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        # Not a priority binding, so ctrl+c copies selected text first and
        # quits only when nothing is selected.
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, auth=None, engine=None, keys=None):
        super().__init__()
        from whatsmynote.app.client import EngineClient
        from whatsmynote.app.config import API_URL, ModelKeyStore

        if auth is None:
            from whatsmynote.app.auth import SupabaseAuth
            auth = SupabaseAuth()
        self.auth = auth
        self.keys = keys or ModelKeyStore()
        self.engine = engine or EngineClient(API_URL, auth.access_token, self.keys.load)

    def on_mount(self) -> None:
        self.register_theme(THEME)
        self.theme = THEME.name
        self.push_screen(MainScreen())

    def copy_to_clipboard(self, text: str) -> None:
        # Terminals that ignore the escape code Textual uses, like macOS
        # Terminal, still get the text through the system clipboard.
        super().copy_to_clipboard(text)
        if sys.platform == "darwin" and shutil.which("pbcopy"):
            try:
                subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=False, timeout=2)
            except (OSError, subprocess.SubprocessError):
                pass
