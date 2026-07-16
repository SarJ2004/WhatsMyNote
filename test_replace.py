import re

with open("d:\\HelloWorld\\Projects\\WhatsMyNote\\whatsmynote\\app\\tui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace CSS
css_search = """    #chat-log {
        height: 1fr;
        background: transparent;
        border: none;
        padding: 0 4;
    }"""
css_replace = """    .startup-logo {
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
    }"""
content = content.replace(css_search, css_replace)

# Replace get_startup_renderable
startup_search = """def get_startup_renderable(width=None):
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
    
    return Group(
        Text("\\n\\n\\n\\n"),
        Align.center(Text.from_markup(LOGO.strip()), width=width),
        Text("\\n"),
        Align.center(table, width=width)
    )"""
startup_replace = """def get_commands_table():
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
    return table"""
content = content.replace(startup_search, startup_replace)

# Replace compose
compose_search = """    def compose(self) -> ComposeResult:
        yield Label("not logged in", id="header-user")
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        from textual.containers import Center
        yield Center(ThinkingIndicator(id="thinking-indicator"))
        yield InputArea()
        yield CustomFooter()"""
compose_replace = """    def compose(self) -> ComposeResult:
        yield Label("not logged in", id="header-user")
        
        from textual.containers import Vertical, Center
        with Vertical(id="startup-container"):
            yield Static("\\n\\n\\n")
            with Center():
                yield Static(LOGO.strip(), classes="startup-logo")
            yield Static("\\n")
            with Center():
                yield Static(get_commands_table(), classes="startup-table")
            yield Static("\\n")
            with Center():
                yield Static("", id="startup-messages")
                
        yield RichLog(id="chat-log", markup=True, highlight=False, wrap=True)
        yield Center(ThinkingIndicator(id="thinking-indicator"))
        yield InputArea()
        yield CustomFooter()"""
content = content.replace(compose_search, compose_replace)

# Replace on_mount and on_resize
resize_search = """    def on_mount(self) -> None:
        self.query_one("#main-input").focus()
        self._chat_started = False
        
    def on_resize(self, event) -> None:
        if getattr(self, "_chat_started", False):
            return
            
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        
        # event.size.width is the true terminal width. 
        # Subtract 4 to account for RichLog's `padding: 1 2`
        width = event.size.width - 4
        log.write(get_startup_renderable(width=width))
        
        # update user label
        self.update_user_label()
        
        user = load_session()
        if user:
            log.write(f"\\n[#888888]restored session for {user.email}[/#888888]")
            
        from whatsmynote.app.config import get_groq_api_key
        if not get_groq_api_key():
            log.write("\\n[#ffaa55]warning: GROQ_API_KEY not set. please run /config to set it up.[/#ffaa55]")"""
resize_replace = """    def on_mount(self) -> None:
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
            self.query_one("#startup-messages", Static).update("\\n".join(messages))"""
content = content.replace(resize_search, resize_replace)

# Replace on_input_submitted
submit_search = """    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._chat_started = True
        val = event.value.strip()"""
submit_replace = """    def on_input_submitted(self, event: Input.Submitted) -> None:
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
            
        val = event.value.strip()"""
content = content.replace(submit_search, submit_replace)

# Replace clear command
clear_search = """                elif val == "/clear":
                    log.clear()
                    self._chat_started = False
                    width = self.size.width - 4
                    log.write(get_startup_renderable(width=width))"""
clear_replace = """                elif val == "/clear":
                    log.clear()
                    self._chat_started = False
                    log.display = False
                    self.query_one("#startup-container").display = True"""
content = content.replace(clear_search, clear_replace)

with open("d:\\HelloWorld\\Projects\\WhatsMyNote\\whatsmynote\\app\\tui.py", "w", encoding="utf-8") as f:
    f.write(content)
