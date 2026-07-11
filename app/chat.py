"""Chat loop — the main interactive CLI with HITL support."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from core.graph import compiled_graph
from app.render import render_result
from app.setup import ensure_initial_setup
from app.selector import display_search_results

console = Console()

# Global state to persist between turns
app_state = {}

def _invoke(message: str) -> dict:
    """Invoke the stateless graph with the accumulated state."""
    global app_state
    app_state["raw_text"] = message
    app_state = compiled_graph.invoke(app_state)
    return app_state

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
            from core.config import set_groq_api_key
            new_key = Prompt.ask("Enter new Groq API Key", password=True)
            if new_key:
                set_groq_api_key(new_key.strip())
                console.print("[green]API Key updated successfully.[/green]")
            else:
                console.print("[yellow]API Key update cancelled.[/yellow]")
            continue

        state = _invoke(message)

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
                
                state = compiled_graph.invoke(app_state)
                app_state = state
                render_result(state)
            else:
                console.print("[dim]Operation cancelled.[/dim]")
            continue

        render_result(state)


def main() -> None:
    ensure_initial_setup()
    run_chat_loop()
