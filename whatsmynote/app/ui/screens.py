from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog, Static
from textual.containers import Center
from textual.binding import Binding

from whatsmynote.app.auth import load_session
from whatsmynote.app.config import get_model_key, set_model_key
from whatsmynote.app.ui.constants import LOGO, get_commands_table
from whatsmynote.app.ui.widgets import CustomFooter, InputArea, ThinkingIndicator
from whatsmynote.app.ui.mixins.auth import AuthMixin
from whatsmynote.app.ui.mixins.onboarding import OnboardingMixin
from whatsmynote.app.ui.mixins.chat import ChatMixin

class MainScreen(Screen, AuthMixin, OnboardingMixin, ChatMixin):
    CSS_PATH = "screens.tcss"
    
    BINDINGS = [
        Binding("/", "focus_input", "Focus Input", show=False),
    ]

    def action_focus_input(self) -> None:
        self.query_one("#main-input").focus()

    def __init__(self):
        super().__init__()
        self.state = "IDLE"
        self.temp_email = ""
        self.history = []
        self.history_index = 0
        self.onboarding_data = {}

    def compose(self) -> ComposeResult:
        yield Label("not logged in", id="header-user")
        
        from textual.containers import Vertical
        with Vertical(id="startup-container"):
            yield Static("\n\n\n")
            with Center():
                yield Static(LOGO.strip(), classes="startup-logo")
            yield Static("\n")
            with Center():
                yield Static(get_commands_table(), classes="startup-table")
            yield Static("\n")
            with Center():
                yield Static("", id="startup-messages")
                
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield Center(ThinkingIndicator(id="thinking-indicator"))
        yield InputArea()
        yield CustomFooter()

    def update_user_label(self):
        user = load_session()
        lbl = self.query_one("#header-user", Label)
        if user:
            metadata = user.user_metadata or {}
            full_name = metadata.get("full_name") or metadata.get("name") or ""
            name = full_name.split(" ")[0] if full_name else user.email.split("@")[0]
            lbl.update(name)
        else:
            lbl.update("not logged in")

    def update_hints(self, left: str, right: str = "WhatsMyNote AI Assistant"):
        self.query_one("#hint-left", Label).update(left)
        self.query_one("#hint-right", Label).update(right)

    def set_state(self, new_state: str):
        self.state = new_state
        if new_state == "IDLE":
            self.update_hints("[bold]enter[/bold] send  [bold]/[/bold] focus  /login  /logout  /config  /clear")
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
        elif new_state.startswith("OB_"):
            self.update_hints("[bold]enter[/bold] submit/default", "Onboarding")

    def cancel_flow(self):
        log = self.query_one("#chat-log", RichLog)
        was_in_flow = False
        
        if self.state != "IDLE":
            was_in_flow = True
            
        if was_in_flow:
            log.write("[#888888]cancelled.[/#888888]")
            self.set_state("IDLE")
            inp = self.query_one("#main-input", Input)
            inp.password = False
            inp.value = ""


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
        self._chat_started = False
        self.update_user_label()
        
        messages = []
        user = load_session()
        if user:
            metadata = user.user_metadata or {}
            full_name = metadata.get("full_name") or metadata.get("name") or ""
            name = full_name.split(" ")[0] if full_name else user.email.split("@")[0]
            messages.append(f"[#888888]Welcome back, {name}! Let's talk money 💸[/#888888]")
            self.check_onboarding_status()
            
        if not get_model_key():
            messages.append("[#ffaa55]No model key saved. Run /config to set one.[/#ffaa55]")
            
        if messages:
            self.query_one("#startup-messages", Static).update("\n".join(messages))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not getattr(self, "_chat_started", False):
            self._chat_started = True
            self.query_one("#startup-container").display = False
            log = self.query_one("#chat-log", RichLog)
            log.display = True
            
            user = load_session()
            if user:
                metadata = user.user_metadata or {}
                full_name = metadata.get("full_name") or metadata.get("name") or ""
                name = full_name.split(" ")[0] if full_name else user.email.split("@")[0]
                log.write(f"[#888888]Session restored for {name}. Let's go! 🚀[/#888888]")
            if not get_model_key():
                log.write("[#ffaa55]No model key saved. Run /config to set one.[/#ffaa55]")
            
        val = event.value.strip()
        inp = event.input
        inp.value = ""
        log = self.query_one("#chat-log", RichLog)

        if not val and not self.state.startswith("OB_"):
            return
            
        if self.state == "IDLE":
            self.history.append(val)
            self.history_index = len(self.history)
            
        if val.lower() == 'q' and self.state != "IDLE":
            if self.state.startswith("OB_"):
                log.write(f"\n[#ffaa55]> {val}[/#ffaa55]")
                log.write("[#ffaa55]Initial setup is required. Please complete it.[/#ffaa55]")
                return
            log.write(f"\n[#ffaa55]> {val}[/#ffaa55]")
            log.write("[#888888]cancelled.[/#888888]")
            self.set_state("IDLE")
            inp.password = False
            return

        if self.state != "IDLE":
            display_val = "***" if inp.password else val
            log.write(f"\n[#ffaa55]> {display_val}[/#ffaa55]")

        self.handle_state(val, log, inp)

    def handle_state(self, val: str, log: RichLog, inp: Input) -> None:
        if self.state == "IDLE":
            log.write(f"\n[#ffaa55]> {val}[/#ffaa55]")
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
                    self._chat_started = False
                    log.display = False
                    self.query_one("#startup-container").display = True
                elif val == "/config":
                    log.write("Enter your model key:")
                    self.set_state("CONFIG_API_KEY")
                    inp.password = True
                elif val in ["/quit", "/exit"]:
                    self.app.exit()
                else:
                    log.write("[#ffaa55]unknown command. try /login, /config, or /clear[/#ffaa55]")
            else:
                user = load_session()
                if not user:
                    log.write("[#ffaa55]you must be logged in to chat. use /login or /signup[/#ffaa55]")
                    return
                if not get_model_key():
                    log.write("[#ffaa55]Model key missing. Use /config to set it.[/#ffaa55]")
                    return
                self.do_chat(val)

        elif self.state == "CONFIG_API_KEY":
            set_model_key(val)
            log.write("[#dddddd]Model key saved.[/#dddddd]")
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

        elif self.state == "OB_ACC_NAME":
            self.onboarding_data["name"] = val or "Cash"
            self.set_state("OB_ACC_BAL")
            log.write("Opening balance, in the smallest unit? [Default: 0]")

        elif self.state == "OB_ACC_BAL":
            try:
                bal = int(val) if val else 0
            except ValueError:
                log.write("[#ffaa55]Enter a whole number.[/#ffaa55]")
                return
            self.onboarding_data["opening_balance"] = bal
            self.do_onboarding_setup()
