"""Chat loop — the main interactive CLI with HITL support."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
import time
import os

from whatsmynote.app.render import render_result
from whatsmynote.app.setup import ensure_initial_setup
from whatsmynote.app.selector import display_search_results

console = Console()

# Global state to persist between turns
app_state = {}

def _send_state() -> dict:
    global app_state
    import requests
    from whatsmynote.app.config import API_URL, get_groq_api_key
    from whatsmynote.app.auth import get_supabase
    
    session = get_supabase().auth.get_session()
    token = session.access_token if session else ""
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Groq-Api-Key": get_groq_api_key() or ""
    }
    payload = {"message": app_state.get("raw_text", ""), "state": app_state}
    
    try:
        response = requests.post(f"{API_URL}/chat", json=payload, headers=headers)
        response.raise_for_status()
        app_state = response.json()["state"]
    except Exception as e:
        console.print(f"[red]Error communicating with backend: {e}[/red]")
        
    return app_state

def _invoke(message: str) -> dict:
    """Invoke the stateless graph via backend API."""
    global app_state
    app_state["raw_text"] = message
    return _send_state()
def run_chat_loop() -> None:
    console.print(
        Panel.fit(
            "[bold]WhatsMyNote CLI[/bold]\nType finance messages. Use [bold]exit[/bold] or [bold]quit[/bold] to stop.",
            border_style="blue",
        )
    )

    global app_state

    while True:
        message = Prompt.ask("[bold blue]You[/bold blue]")
        msg_lower = message.strip().lower()
        if msg_lower in {"exit", "quit", "q"}:
            console.print("[dim]Bye.[/dim]")
            break
        elif msg_lower == "/clear":
            console.clear()
            continue
        elif msg_lower == "/config":
            from whatsmynote.app.config import set_groq_api_key
            new_key = Prompt.ask("Enter new Groq API Key", password=True)
            if new_key:
                set_groq_api_key(new_key.strip())
                console.print("[green]API Key updated successfully.[/green]")
            else:
                console.print("[yellow]API Key update cancelled.[/yellow]")
            continue
        elif msg_lower == "/logout":
            from whatsmynote.app.auth import get_supabase, SESSION_FILE
            try:
                get_supabase().auth.sign_out()
                if os.path.exists(SESSION_FILE):
                    os.remove(SESSION_FILE)
                if "CURRENT_USER_ID" in os.environ:
                    del os.environ["CURRENT_USER_ID"]
                console.print("[green]Logged out successfully.[/green]")
            except Exception as e:
                console.print(f"[red]Error logging out: {e}[/red]")
            break

        start_time = time.time()
        state = _invoke(message)
        end_time = time.time()
        
        if os.environ.get("ENV") == "dev":
            console.print(f"[dim yellow]DEBUG: Response time: {end_time - start_time:.2f}s[/dim yellow]")

        # HITL: If the system needs the user to select a record
        if state.get("awaiting_selection") and state.get("search_results"):
            render_result(state)  # Show the "please select" message

            record_type = state.get("record_type", "record")
            intent = state.get("intent")
            
            selected_result = display_search_results(
                state["search_results"], record_type, multiselect=(intent == "delete")
            )

            if selected_result:
                # Set selection and manually re-invoke
                app_state["awaiting_selection"] = False
                if isinstance(selected_result, list):
                    app_state["raw_text"] = f"selected multiple: {selected_result}"
                    app_state["selected_record_ids"] = selected_result
                    app_state["selected_record_id"] = None
                else:
                    app_state["raw_text"] = f"select {selected_result}"
                    app_state["selected_record_id"] = selected_result
                    app_state["selected_record_ids"] = None
                
                state = _send_state()
                app_state = state
                render_result(state)
            else:
                console.print("[dim]Operation cancelled.[/dim]")
            continue

        render_result(state)


def main() -> None:
    from whatsmynote.app.config import ensure_env_config
    ensure_env_config()
    from whatsmynote.app.auth import ensure_authenticated
    ensure_authenticated()
    from whatsmynote.app.setup import ensure_initial_setup
    ensure_initial_setup()
    run_chat_loop()
