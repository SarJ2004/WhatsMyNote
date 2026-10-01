from textual.binding import Binding
from textual.containers import Horizontal
from textual.suggester import SuggestFromList
from textual.widgets import Input, Label, Static

from whatsmynote.app.ui.constants import COMMANDS

WORKING_FRAMES = ["working ·  ", "working ·· ", "working ···", "working  ··", "working   ·"]


class TopBar(Horizontal):
    def compose(self):
        yield Label("WhatsMyNote", id="brand")
        yield Label("", id="who")


class Message(Static):
    """One entry in the conversation. Text in it can be selected and copied."""

    def __init__(self, renderable, kind: str):
        super().__init__(renderable, classes=f"message {kind}")
        self.source = renderable

    def update(self, renderable="", *, layout: bool = True) -> None:
        self.source = renderable
        super().update(renderable, layout=layout)


class HistoryInput(Input):
    """The one line people type into. Up and down bring back earlier lines,
    and a typed slash command is completed from the command list."""

    BINDINGS = [
        Binding("up", "history(-1)", "Previous line", show=False),
        Binding("down", "history(1)", "Next line", show=False),
        Binding("escape", "screen.cancel_pending", "Cancel", show=False),
    ]

    def __init__(self, **kwargs):
        super().__init__(
            suggester=SuggestFromList([command for command, _ in COMMANDS], case_sensitive=False),
            **kwargs,
        )
        self.history: list[str] = []
        self.history_index = 0

    def remember(self, line: str) -> None:
        if line and (not self.history or self.history[-1] != line):
            self.history.append(line)
        self.history_index = len(self.history)

    def action_history(self, step: int) -> None:
        if not self.history:
            return
        self.history_index = max(0, min(len(self.history), self.history_index + step))
        self.value = self.history[self.history_index] if self.history_index < len(self.history) else ""
        self.cursor_position = len(self.value)


class HintBar(Horizontal):
    def compose(self):
        yield Label("", id="hint-left")
        yield Label("", id="hint-right")

    def on_mount(self) -> None:
        self._frame = 0
        self._timer = self.set_interval(0.15, self._tick, pause=True)

    def working(self, busy: bool) -> None:
        right = self.query_one("#hint-right", Label)
        if busy:
            self._frame = 0
            right.update(WORKING_FRAMES[0])
            self._timer.resume()
        else:
            self._timer.pause()
            right.update("")

    def _tick(self) -> None:
        self._frame = (self._frame + 1) % len(WORKING_FRAMES)
        self.query_one("#hint-right", Label).update(WORKING_FRAMES[self._frame])
