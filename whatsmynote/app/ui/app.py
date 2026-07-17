from textual.app import App
from textual.binding import Binding

from whatsmynote.app.ui.screens import MainScreen

class WhatsMyNoteApp(App):
    BINDINGS = [
        Binding("ctrl+q", "", "Unbound", show=False)
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())
