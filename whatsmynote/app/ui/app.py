from textual.app import App
from textual.binding import Binding

from whatsmynote.app.ui.screens import MainScreen

class WhatsMyNoteApp(App):
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True)
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())
