from textual.app import App, ComposeResult
from textual.widgets import Static, RichLog
from textual.containers import Vertical
from rich.align import Align
from rich.text import Text

DOLLAR_FRAMES = [
    "[ $       ]",
    "[  $      ]",
    "[   $     ]",
]

LOGO = """
█   █ █   █ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim] █[dim]▀[/dim]█[dim]▀[/dim]█ █   █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim]
█ █ █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█   █   █[dim]▀▀▀[/dim]█ █ █ █ █[dim]▄▄▄[/dim]█ █   █ █   █   █   █[dim]▀▀▀ [/dim]
█[dim]▄[/dim]█[dim]▄[/dim]█ █   █ █   █   █   [dim]▄▄▄▄[/dim]█ █   █ [dim]▄▄▄▄[/dim]█ █   █ █[dim]▄▄▄[/dim]█   █   █[dim]▄▄▄▄[/dim]
"""

class ThinkingIndicator(Static):
    def on_mount(self):
        self.frame_idx = 0
        self.phrase = "Looking for spare change..."
        self.set_interval(0.2, self.update_animation)
        
    def update_animation(self):
        self.frame_idx = (self.frame_idx + 1) % len(DOLLAR_FRAMES)
        frame = DOLLAR_FRAMES[self.frame_idx]
        content = f"[#ffaa55]{frame}[/#ffaa55]\n[#888888]{self.phrase}[/#888888]"
        self.update(Align.center(content))

class TestApp(App):
    CSS = """
    #thinking-indicator {
        width: 100%;
        height: 3;
        background: red;
    }
    """
    def compose(self) -> ComposeResult:
        yield RichLog(id="log")
        yield ThinkingIndicator(id="thinking-indicator")
        
    def on_mount(self):
        # use a timer to wait for real width
        self.set_timer(0.5, self.do_log)
        
    def do_log(self):
        log = self.query_one("#log", RichLog)
        text = Text.from_markup(LOGO.strip('\n'))
        log.write(Align.center(text))

if __name__ == "__main__":
    app = TestApp()
    app.run()
