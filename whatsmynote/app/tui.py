import webbrowser
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog
from textual.containers import Container, Horizontal, Center, Vertical
from textual.binding import Binding
from textual import work
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.console import Group

from whatsmynote.app.auth import (
    login_with_password, signup_with_password, 
    start_oauth, wait_for_auth_code,
    reset_password_for_email, update_password,
    load_session, logout
)
from whatsmynote.app.config import get_groq_api_key, set_groq_api_key

LOGO = """
█   █ █   █ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim] █[dim]▀[/dim]█[dim]▀[/dim]█ █   █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█ [dim]▀▀[/dim]█[dim]▀▀[/dim] █[dim]▀▀▀▀[/dim]
█ █ █ █[dim]▀▀▀[/dim]█ █[dim]▀▀▀[/dim]█   █   █[dim]▀▀▀[/dim]█ █ █ █ █[dim]▄▄▄[/dim]█ █   █ █   █   █   █[dim]▀▀▀ [/dim]
█[dim]▄[/dim]█[dim]▄[/dim]█ █   █ █   █   █   [dim]▄▄▄▄[/dim]█ █   █ [dim]▄▄▄▄[/dim]█ █   █ █[dim]▄▄▄[/dim]█   █   █[dim]▄▄▄▄[/dim]
"""

class CustomFooter(Container):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("whatsmynote v0.1.3  ~", id="footer-left")
            yield Label("tab | [reverse] SWITCH MODE [/reverse]", id="footer-right", markup=True)

class HistoryInput(Input):
    BINDINGS = [
        Binding("up", "history_up", "Previous command", show=False),
        Binding("down", "history_down", "Next command", show=False),
    ]

    def action_history_up(self):
        # We find the parent MainScreen and trigger its history handler
        for node in self.ancestors:
            if isinstance(node, MainScreen):
                node.history_up()
                break

    def action_history_down(self):
        for node in self.ancestors:
            if isinstance(node, MainScreen):
                node.history_down()
                break

class InputArea(Container):
    def compose(self) -> ComposeResult:
        with Horizontal(id="input-row"):
            yield Label(">", id="input-prompt")
            yield HistoryInput(id="main-input")
        with Horizontal(id="input-hints"):
            yield Label("[bold]enter[/bold] send", id="hint-left", markup=True)
            yield Label("WhatsMyNote AI Assistant", id="hint-right")

def get_startup_renderable():
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="#ffaa55")
    table.add_column(style="#dddddd")
    table.add_column(style="#888888")
    
    commands = [
        ("/login", "login to account", "ctrl+x l"),
        ("/signup", "create account", "ctrl+x s"),
        ("/config", "set api key", "ctrl+x c"),
        ("/logout", "log out", "ctrl+x o"),
    ]
    for cmd, desc, key in commands:
        table.add_row(cmd, desc, key)
    
    logo_text = Text.from_markup(LOGO.strip('\n'))
    group = Group(
        Text("\n\n\n\n"),
        Align.center(logo_text), 
        Text("\n"),
        Align.center(table)
    )
    return group

class MainScreen(Screen):
    CSS = """
    MainScreen {
        background: #000000;
        color: #e0e0e0;
    }

    * {
        scrollbar-size: 0 0;
    }

    #chat-log {
        height: 1fr;
        background: transparent;
        border: none;
        padding: 0 4;
    }

    InputArea {
        dock: bottom;
        height: 3;
        margin-bottom: 2;
        padding: 0 2;
    }

    #input-row {
        height: 1;
    }

    #input-prompt {
        color: #ffaa55;
        margin-right: 1;
    }

    #main-input {
        width: 1fr;
        border: none;
        background: transparent;
        padding: 0;
    }
    
    #main-input:focus {
        border: none;
    }

    #input-hints {
        height: 1;
        margin-top: 1;
    }

    #hint-left {
        color: #888888;
        width: 1fr;
    }

    #hint-right {
        color: #888888;
        content-align: right middle;
    }

    CustomFooter {
        dock: bottom;
        height: 1;
        background: #000000;
        color: #888888;
        padding: 0 1;
    }

    #footer-left {
        width: 1fr;
    }

    #footer-right {
        content-align: right middle;
        color: #55aaff;
    }
    """

    def __init__(self):
        super().__init__()
        self.state = "IDLE"
        self.temp_email = ""
        self.history = []
        self.history_index = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", markup=True, highlight=True, wrap=True)
        yield InputArea()
        yield CustomFooter()

    def update_hints(self, left: str, right: str = "WhatsMyNote AI Assistant"):
        self.query_one("#hint-left", Label).update(left)
        self.query_one("#hint-right", Label).update(right)

    def set_state(self, new_state: str):
        self.state = new_state
        if new_state == "IDLE":
            self.update_hints("[bold]enter[/bold] send")
        elif new_state == "AUTH_MODE_SELECT":
            self.update_hints("[bold]l[/bold] login  [bold]s[/bold] signup  [bold]f[/bold] forgot  [bold]o[/bold] oauth  [bold]q[/bold] cancel", "Auth Mode")
        elif new_state in ["AUTH_EMAIL", "AUTH_FORGOT_EMAIL"]:
            self.update_hints("[bold]enter[/bold] submit email  [bold]q[/bold] cancel", "Auth Mode")
        elif new_state in ["AUTH_PASSWORD", "AUTH_FORGOT_NEW_PASS"]:
            self.update_hints("[bold]enter[/bold] submit password  [bold]q[/bold] cancel", "Auth Mode")
        elif new_state == "AUTH_OAUTH_PROVIDER":
            self.update_hints("[bold]google[/bold] or [bold]github[/bold]  [bold]q[/bold] cancel", "Auth Mode")
        elif new_state == "CONFIG_API_KEY":
            self.update_hints("[bold]enter[/bold] save api key  [bold]q[/bold] cancel", "Config Mode")

    def history_up(self):
        inp = self.query_one("#main-input", Input)
        if self.history and self.history_index > 0:
            self.history_index -= 1
            inp.value = self.history[self.history_index]
            inp.cursor_position = len(inp.value)

    def history_down(self):
        inp = self.query_one("#main-input", Input)
        if self.history and self.history_index < len(self.history) - 1:
            self.history_index += 1
            inp.value = self.history[self.history_index]
            inp.cursor_position = len(inp.value)
        elif self.history_index == len(self.history) - 1:
            self.history_index = len(self.history)
            inp.value = ""

    def on_mount(self) -> None:
        self.query_one("#main-input").focus()
        log = self.query_one("#chat-log", RichLog)
        log.write(get_startup_renderable())
        
        user = load_session()
        if user:
            log.write(f"\n[#888888]restored session for {user.email}[/#888888]")
            
        if not get_groq_api_key():
            log.write("\n[#ffaa55]warning: GROQ_API_KEY not set. please run /config to set it up.[/#ffaa55]")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        inp = event.input
        inp.value = ""
        log = self.query_one("#chat-log", RichLog)

        if not val:
            return
            
        if self.state == "IDLE":
            self.history.append(val)
            self.history_index = len(self.history)
            
        if val.lower() == 'q' and self.state != "IDLE":
            log.write(f"[#888888]> {val}[/#888888]")
            log.write("[#888888]cancelled.[/#888888]")
            self.set_state("IDLE")
            inp.password = False
            return

        if self.state != "IDLE":
            display_val = "***" if inp.password else val
            log.write(f"[#888888]> {display_val}[/#888888]")

        self.handle_state(val, log, inp)

    def handle_state(self, val: str, log: RichLog, inp: Input) -> None:
        if self.state == "IDLE":
            log.write(f"[#888888]> {val}[/#888888]")
            if val.startswith("/"):
                if val in ["/login", "/signup"]:
                    log.write("Do you want to (L)og in, (S)ign up, (F)orgot Password, or (O)Auth [Google/GitHub]?")
                    self.set_state("AUTH_MODE_SELECT")
                    inp.password = False
                elif val == "/logout":
                    log.write("[#888888]logging out...[/#888888]")
                    self.do_logout()
                elif val == "/clear":
                    log.clear()
                    log.write(get_startup_renderable())
                elif val == "/config":
                    log.write("Enter your GROQ API Key:")
                    self.set_state("CONFIG_API_KEY")
                    inp.password = True
                else:
                    log.write("[#ffaa55]unknown command. try /login, /config, or /clear[/#ffaa55]")
            else:
                user = load_session()
                if not user:
                    log.write("[#ffaa55]you must be logged in to chat. use /login or /signup[/#ffaa55]")
                    return
                if not get_groq_api_key():
                    log.write("[#ffaa55]groq api key missing. use /config to set it up.[/#ffaa55]")
                    return
                log.write(f"[#dddddd]Sending message: {val}[/#dddddd]")

        elif self.state == "CONFIG_API_KEY":
            set_groq_api_key(val)
            log.write("[#dddddd]groq api key saved successfully![/#dddddd]")
            inp.password = False
            self.set_state("IDLE")

        elif self.state == "AUTH_MODE_SELECT":
            action = val.lower()
            if action in ["l", "s"]:
                self.action_type = action
                log.write("Email:")
                self.set_state("AUTH_EMAIL")
            elif action == "f":
                log.write("Email for password reset:")
                self.set_state("AUTH_FORGOT_EMAIL")
            elif action == "o":
                log.write("Which provider? (google/github)")
                self.set_state("AUTH_OAUTH_PROVIDER")
            else:
                log.write("[#ffaa55]invalid choice. press q to cancel.[/#ffaa55]")

        elif self.state == "AUTH_EMAIL":
            self.temp_email = val
            log.write("Password:")
            inp.password = True
            self.set_state("AUTH_PASSWORD")

        elif self.state == "AUTH_PASSWORD":
            inp.password = False
            self.set_state("IDLE")
            if self.action_type == "l":
                log.write(f"[#888888]attempting login for {self.temp_email}...[/#888888]")
                self.do_login(self.temp_email, val)
            else:
                log.write(f"[#888888]attempting signup for {self.temp_email}...[/#888888]")
                self.do_signup(self.temp_email, val)

        elif self.state == "AUTH_FORGOT_EMAIL":
            self.temp_email = val
            self.set_state("IDLE")
            log.write(f"[#888888]sending password reset link to {val}...[/#888888]")
            self.do_password_reset(val)

        elif self.state == "AUTH_FORGOT_NEW_PASS":
            inp.password = False
            self.set_state("IDLE")
            log.write("[#888888]updating password...[/#888888]")
            self.do_password_update(val)

        elif self.state == "AUTH_OAUTH_PROVIDER":
            self.set_state("IDLE")
            provider = val.lower()
            if provider in ["google", "github"]:
                log.write(f"[#888888]opening browser for {provider.capitalize()} auth...[/#888888]")
                self.do_oauth(provider)
            else:
                log.write("[#ffaa55]invalid provider. try google or github.[/#ffaa55]")

    @work(thread=True)
    def do_login(self, email, password):
        log = self.query_one("#chat-log", RichLog)
        try:
            user = login_with_password(email, password)
            self.app.call_from_thread(log.write, f"[#dddddd]logged in successfully as {user.email}[/#dddddd]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]login failed: {str(e)}[/#ffaa55]")

    @work(thread=True)
    def do_signup(self, email, password):
        log = self.query_one("#chat-log", RichLog)
        try:
            user = signup_with_password(email, password)
            self.app.call_from_thread(log.write, "[#dddddd]sign up successful! you can now log in.[/#dddddd]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]sign up failed: {str(e)}[/#ffaa55]")

    @work(thread=True)
    def do_oauth(self, provider):
        log = self.query_one("#chat-log", RichLog)
        try:
            url = start_oauth(provider)
            webbrowser.open(url)
            self.app.call_from_thread(log.write, "[#888888]waiting for authentication code from browser...[/#888888]")
            user = wait_for_auth_code()
            if user:
                self.app.call_from_thread(log.write, f"[#dddddd]successfully authenticated as {user.email}![/#dddddd]")
            else:
                self.app.call_from_thread(log.write, "[#ffaa55]authentication failed: no code received.[/#ffaa55]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]oauth failed: {str(e)}[/#ffaa55]")

    @work(thread=True)
    def do_password_reset(self, email):
        log = self.query_one("#chat-log", RichLog)
        try:
            reset_password_for_email(email)
            self.app.call_from_thread(log.write, "[#888888]password reset email sent. check your inbox and click the link...[/#888888]")
            
            user = wait_for_auth_code()
            if user:
                self.app.call_from_thread(self.prompt_new_password)
            else:
                self.app.call_from_thread(log.write, "[#ffaa55]password reset failed: no code received.[/#ffaa55]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]password reset error: {str(e)}[/#ffaa55]")
            
    def prompt_new_password(self):
        log = self.query_one("#chat-log", RichLog)
        inp = self.query_one("#main-input", Input)
        log.write("Enter new password:")
        inp.password = True
        self.set_state("AUTH_FORGOT_NEW_PASS")

    @work(thread=True)
    def do_password_update(self, new_password):
        log = self.query_one("#chat-log", RichLog)
        try:
            update_password(new_password)
            self.app.call_from_thread(log.write, "[#dddddd]password updated successfully! you are now logged in.[/#dddddd]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]password update failed: {str(e)}[/#ffaa55]")
            
    @work(thread=True)
    def do_logout(self):
        log = self.query_one("#chat-log", RichLog)
        try:
            logout()
            self.app.call_from_thread(log.write, "[#dddddd]logged out successfully.[/#dddddd]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]logout failed: {str(e)}[/#ffaa55]")

class WhatsMyNoteApp(App):
    def on_mount(self) -> None:
        self.push_screen(MainScreen())
