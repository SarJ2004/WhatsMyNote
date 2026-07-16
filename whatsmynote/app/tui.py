import os
import requests
import webbrowser
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Input, Label, RichLog, Static
from textual.containers import Container, Horizontal
from textual.binding import Binding
from textual import work
from rich.text import Text
from rich.table import Table
from rich import box
from rich.align import Align
from rich.console import Group
import random

from whatsmynote.app.auth import (
    login_with_password, signup_with_password, 
    start_oauth, wait_for_auth_code,
    reset_password_for_email, update_password,
    load_session, logout, get_supabase
)
from whatsmynote.app.config import get_groq_api_key, set_groq_api_key, API_URL

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

def get_commands_table():
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
    return table

QUIRKY_PHRASES = [
    "Crunching your numbers...",
    "Looking for spare change...",
    "Consulting the finance oracle...",
    "Digging through receipts...",
    "Balancing the ledger...",
    "Tracking down that last coffee...",
    "Auditing your wallet...",
]

DOLLAR_FRAMES = [
    "[ $       ]",
    "[  $      ]",
    "[   $     ]",
    "[    $    ]",
    "[     $   ]",
    "[      $  ]",
    "[       $ ]",
    "[        $]",
    "[       $ ]",
    "[      $  ]",
    "[     $   ]",
    "[    $    ]",
    "[   $     ]",
    "[  $      ]",
]

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
        from rich.text import Text
        from rich.align import Align
        from rich.console import Group
        
        top = Align.center(Text.from_markup(f"[#ffaa55]{frame}[/#ffaa55]"))
        bottom = Align.center(Text.from_markup(f"[#888888]{self.phrase}[/#888888]"))
        
        self.update(Group(top, bottom))

class MainScreen(Screen):
    CSS = """
    MainScreen {
        background: #000000;
        color: #e0e0e0;
    }

    * {
        scrollbar-size: 0 0;
    }

    .startup-logo {
        width: auto;
        content-align: center middle;
    }
    .startup-table {
        width: auto;
        content-align: center middle;
    }
    #startup-messages {
        width: auto;
        content-align: center middle;
    }
    #chat-log {
        height: 1fr;
        background: transparent;
        border: none;
        padding: 0 4;
        display: none;
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

    #header-user {
        dock: top;
        width: 100%;
        content-align: right middle;
        color: #888888;
        padding: 0 1;
        height: 1;
        background: transparent;
    }

    #header-user {
        dock: top;
        width: 100%;
        content-align: right middle;
        color: #888888;
        padding: 0 1;
        height: 1;
        background: transparent;
    }

    #thinking-indicator {
        width: auto;
        height: 3;
        content-align: center middle;
        display: none;
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
        self.app_state = {}
        self.current_search_results = []

    def compose(self) -> ComposeResult:
        yield Label("not logged in", id="header-user")
        
        from textual.containers import Vertical, Center
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
            lbl.update(user.email)
        else:
            lbl.update("not logged in")

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
        elif new_state == "AWAITING_SELECTION":
            self.update_hints("[bold]enter[/bold] select option  [bold]q[/bold] cancel", "Selection Mode")

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
            messages.append(f"[#888888]restored session for {user.email}[/#888888]")
            
        from whatsmynote.app.config import get_groq_api_key
        if not get_groq_api_key():
            messages.append("[#ffaa55]warning: GROQ_API_KEY not set. please run /config to set it up.[/#ffaa55]")
            
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
                log.write(f"[#888888]restored session for {user.email}[/#888888]")
            from whatsmynote.app.config import get_groq_api_key
            if not get_groq_api_key():
                log.write("[#ffaa55]warning: GROQ_API_KEY not set. please run /config to set it up.[/#ffaa55]")
            
        val = event.value.strip()
        inp = event.input
        inp.value = ""
        log = self.query_one("#chat-log", RichLog)

        if not val:
            return
            
        if self.state in ["IDLE", "AWAITING_SELECTION"]:
            self.history.append(val)
            self.history_index = len(self.history)
            
        if val.lower() == 'q' and self.state not in ["IDLE", "AWAITING_SELECTION"]:
            log.write(f"\n[#ffaa55]> {val}[/#ffaa55]")
            log.write("[#888888]cancelled.[/#888888]")
            self.set_state("IDLE")
            inp.password = False
            return

        if self.state not in ["IDLE", "AWAITING_SELECTION"]:
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
                    log.write("Enter your GROQ API Key:")
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
                if not get_groq_api_key():
                    log.write("[#ffaa55]groq api key missing. use /config to set it up.[/#ffaa55]")
                    return
                self.do_chat(val)

        elif self.state == "AWAITING_SELECTION":
            log.write(f"\n[#ffaa55]> {val}[/#ffaa55]")
            self.set_state("IDLE")
            self.do_chat(val, is_selection=True)

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
    def do_chat(self, message: str, is_selection: bool = False):
        log = self.query_one("#chat-log", RichLog)
        
        if is_selection:
            try:
                idx = int(message) - 1
                if 0 <= idx < len(self.current_search_results):
                    result = self.current_search_results[idx]
                    result_id = result.get("id")
                    if result_id is not None:
                        self.app_state["awaiting_selection"] = False
                        self.app_state["raw_text"] = f"select {result_id}"
                        self.app_state["selected_record_id"] = result_id
                        self.app_state["selected_record_ids"] = None
                    else:
                        self.app_state["raw_text"] = message
                else:
                    self.app_state["raw_text"] = message
            except ValueError:
                self.app_state["raw_text"] = message
        else:
            self.app_state["raw_text"] = message

        session = get_supabase().auth.get_session()
        token = session.access_token if session else ""
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Groq-Api-Key": get_groq_api_key() or ""
        }
        payload = {"message": self.app_state.get("raw_text", ""), "state": self.app_state}

        indicator = self.query_one("#thinking-indicator", ThinkingIndicator)
        self.app.call_from_thread(indicator.start)

        try:
            response = requests.post(f"{API_URL}/chat", json=payload, headers=headers)
            response.raise_for_status()
            self.app_state = response.json().get("state", {})
            self.app.call_from_thread(indicator.stop)
            self.app.call_from_thread(self.render_backend_response, self.app_state)
        except Exception as e:
            self.app.call_from_thread(indicator.stop)
            self.app.call_from_thread(log.write, f"[#ffaa55]backend error: {e}[/#ffaa55]")

    def render_backend_response(self, state: dict):
        log = self.query_one("#chat-log", RichLog)
        
        if state.get("error"):
            log.write(f"[#ffaa55]Error: {state['error']}[/#ffaa55]")
            return

        answer = state.get("answer")
        query_result = state.get("query_result")
        budget_alerts = state.get("budget_alerts") or []
        chart_config = state.get("chart_config")

        if budget_alerts:
            for alert in budget_alerts:
                log.write(f"[#ffaa55]! Alert: {alert}[/#ffaa55]")

        if query_result is not None:
            if isinstance(query_result, list) and query_result:
                if chart_config:
                    chart = self._render_analytics_chart(query_result, chart_config)
                    if chart:
                        chart_type = chart_config.get("chart_type")
                        if chart_type in ["pie", "donut"]:
                            log.write(f"\n[#dddddd bold]Chart: {chart_config.get('title', '')}[/#dddddd bold]")
                            log.write(Text.from_ansi(chart))
                        else:
                            log.write(f"\n[#dddddd bold]Chart: {chart_config.get('title', '')}[/#dddddd bold]")
                            log.write(Text(chart, style="#888888"))
                
                headers = list(query_result[0].keys())
                table = Table(box=box.SIMPLE, show_edge=False, header_style="#dddddd bold", border_style="#888888")
                for h in headers:
                    table.add_column(str(h), style="#888888")
                for row in query_result:
                    table.add_row(*[str(row.get(h, "")) for h in headers])
                log.write(table)
            elif isinstance(query_result, dict):
                for k, v in query_result.items():
                    log.write(f"[#888888]{k}: {v}[/#888888]")
            else:
                log.write(f"[#888888]{query_result}[/#888888]")

        if answer:
            log.write(f"[#dddddd]{answer}[/#dddddd]")

        if state.get("saved_record_ids"):
            count = len(state["saved_record_ids"])
            log.write(f"[#dddddd]successfully created {count} record(s).[/#dddddd]")
            return

        if state.get("updated_record_id"):
            log.write(f"[#dddddd]record #{state['updated_record_id']} updated successfully.[/#dddddd]")
            return

        if state.get("deleted_record_id"):
            log.write(f"[#dddddd]record #{state['deleted_record_id']} deleted successfully.[/#dddddd]")
            return

        # HITL
        if state.get("awaiting_selection") and state.get("search_results"):
            self.current_search_results = state["search_results"]
            log.write("\n[#dddddd]Please select an option by typing its number:[/#dddddd]")
            for i, res in enumerate(self.current_search_results, 1):
                # We show the title or string representation
                display_str = res.get("title") or res.get("name") or str(res)
                log.write(f"[#888888][{i}] {display_str}[/#888888]")
            self.set_state("AWAITING_SELECTION")

    @work(thread=True)
    def do_login(self, email, password):
        log = self.query_one("#chat-log", RichLog)
        try:
            user = login_with_password(email, password)
            self.app.call_from_thread(log.write, f"[#dddddd]logged in successfully as {user.email}[/#dddddd]")
            self.app.call_from_thread(self.update_user_label)
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
                self.app.call_from_thread(self.update_user_label)
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
            self.app.call_from_thread(self.update_user_label)
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]password update failed: {str(e)}[/#ffaa55]")
            
    @work(thread=True)
    def do_logout(self):
        log = self.query_one("#chat-log", RichLog)
        try:
            logout()
            self.app.call_from_thread(log.write, "[#dddddd]logged out successfully.[/#dddddd]")
            self.app.call_from_thread(self.update_user_label)
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]logout failed: {str(e)}[/#ffaa55]")

    def _render_analytics_chart(self, rows: list[dict], chart_config: dict) -> str | None:
        chart_type = chart_config.get("chart_type")
        if not chart_type or chart_type == "none":
            return None

        x_col = chart_config.get("x_axis")
        y_col = chart_config.get("y_axis")
        if not x_col or not y_col:
            return None
            
        title = chart_config.get("title") or "Analytics Chart"

        if chart_type in ["pie", "donut"]:
            try:
                import termcharts
                data = {}
                for row in rows:
                    k = str(row.get(x_col, ""))
                    v = float(row.get(y_col) or 0)
                    data[k] = v
                
                if chart_type == "donut":
                    chart_obj = termcharts.doughnut(data, title=title)
                else:
                    chart_obj = termcharts.pie(data, title=title)
                    
                return str(chart_obj)
            except Exception:
                chart_type = "bar"

        import plotext as plt
        plt.clf()

        if chart_type == "line":
            plt.date_form("Y-m-d")
            sorted_rows = sorted(rows, key=lambda row: str(row.get(x_col, "")))
            labels = [str(row.get(x_col, "")) for row in sorted_rows]
            values = [float(row.get(y_col) or 0) for row in sorted_rows]
            plt.plot(labels, values, marker="dot")
        else:
            top_rows = sorted(rows, key=lambda row: float(row.get(y_col) or 0), reverse=True)[:15]
            labels = [str(row.get(x_col, "")) for row in top_rows]
            values = [float(row.get(y_col) or 0) for row in top_rows]
            
            if chart_type == "scatter":
                plt.scatter(labels, values)
            else:
                plt.bar(labels, values, orientation="horizontal")
                
        plt.title(title)
        plt.plotsize(60, 20)
        plt.theme("clear")
        
        try:
            return plt.build()
        except Exception:
            plt.theme("pro")
            return plt.build()

class WhatsMyNoteApp(App):
    BINDINGS = [
        Binding("ctrl+q", "", "Unbound", show=False)
    ]

    def on_mount(self) -> None:
        self.push_screen(MainScreen())
