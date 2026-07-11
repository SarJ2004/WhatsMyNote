from __future__ import annotations

from typing import Any

from rich.console import Console
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.prompts.fuzzy import FuzzyPrompt

# Monkey-patch FuzzyPrompt to prevent IndexError when toggling an empty search result
_original_toggle = FuzzyPrompt._handle_toggle_choice
def _safe_toggle(self, event) -> None:
    try:
        _original_toggle(self, event)
    except IndexError:
        pass
FuzzyPrompt._handle_toggle_choice = _safe_toggle

console = Console()

def display_search_results(results: list[dict[str, Any]], record_type: str, multiselect: bool = False) -> int | list[int] | None:
    """Display search results as a fuzzy search menu and prompt user to pick one or more.

    Returns the selected record ID(s), or None if cancelled.
    """
    if not results:
        console.print("[yellow]No records found.[/yellow]")
        return None

    choices = []
    display_keys = [k for k in results[0].keys() if k != "id"]

    for record in results:
        # Build a searchable string out of the values
        parts = []
        for key in display_keys:
            val = record.get(key)
            if val is not None and val != "" and val != "-":
                parts.append(f"{key.title()}: {val}")
        
        display_str = " | ".join(parts)
        choices.append(Choice(value=record.get("id"), name=display_str))

    msg = f"Search and select a {record_type} record (Type to filter, Enter to select, Ctrl-C to cancel):"
    if multiselect:
        msg = f"Search and select multiple {record_type} records (Tab/Space to toggle, Ctrl-A to select all, Enter to confirm):"

    try:
        prompt = inquirer.fuzzy(
            message=msg,
            choices=choices,
            instruction="(Use arrow keys or type to fuzzy search)",
            max_height="60%",
            multiselect=multiselect,
        )

        if multiselect:
            prompt._all_selected = False

            @prompt.register_kb("c-a")
            def _toggle_all(event):
                prompt._all_selected = not getattr(prompt, "_all_selected", False)
                prompt._handle_toggle_all(None, prompt._all_selected)

        choice = prompt.execute()

        return choice
    except KeyboardInterrupt:
        console.print("\n[dim]Selection cancelled.[/dim]")
        return None
