import random
from textual.app import ComposeResult
from textual.widgets import Input, Label, Static
from textual.containers import Container, Horizontal
from textual.binding import Binding
from rich.text import Text
from rich.align import Align
from rich.console import Group

from whatsmynote.app.ui.constants import QUIRKY_PHRASES, DOLLAR_FRAMES

class CustomFooter(Container):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("whatsmynote v0.1.3  ~", id="footer-left")
            yield Label("ctrl+c | [reverse] QUIT [/reverse]", id="footer-right", markup=True)

class HistoryInput(Input):
    BINDINGS = [
        Binding("up", "history_up", "Previous command", show=False),
        Binding("down", "history_down", "Next command", show=False),
        Binding("escape", "cancel_flow", "Cancel flow", show=False),
    ]

    def action_history_up(self):
        from whatsmynote.app.ui.screens import MainScreen
        for node in self.ancestors:
            if isinstance(node, MainScreen):
                node.history_up()
                break

    def action_history_down(self):
        from whatsmynote.app.ui.screens import MainScreen
        for node in self.ancestors:
            if isinstance(node, MainScreen):
                node.history_down()
                break

    def action_cancel_flow(self):
        from whatsmynote.app.ui.screens import MainScreen
        for node in self.ancestors:
            if isinstance(node, MainScreen):
                node.cancel_flow()
                break

class InputArea(Container):
    def compose(self) -> ComposeResult:
        with Horizontal(id="input-row"):
            yield Label(">", id="input-prompt")
            yield HistoryInput(id="main-input")
        with Horizontal(id="input-hints"):
            yield Label("[bold]enter[/bold] send", id="hint-left", markup=True)
            yield Label("WhatsMyNote AI Assistant", id="hint-right")

class ThinkingIndicator(Static):
    def on_mount(self):
        self.frame_idx = 0
        self.phrase = random.choice(QUIRKY_PHRASES)
        self.animation_timer = self.set_interval(0.2, self.update_animation)
        self.display = False
        
    def start(self):
        self.phrase = random.choice(QUIRKY_PHRASES)
        self.display = True
        self.update_animation()
        
    def stop(self):
        self.display = False

    def update_animation(self):
        if not self.display:
            return
        self.frame_idx = (self.frame_idx + 1) % len(DOLLAR_FRAMES)
        frame = DOLLAR_FRAMES[self.frame_idx]
        
        top = Align.center(Text.from_markup(f"[#ffaa55]{frame}[/#ffaa55]"))
        bottom = Align.center(Text.from_markup(f"[#888888]{self.phrase}[/#888888]"))
        
        self.update(Group(top, bottom))
