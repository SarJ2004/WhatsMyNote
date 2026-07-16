"""First-run setup — accounts and budgets."""

from __future__ import annotations

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from whatsmynote.app.config import API_URL, get_groq_api_key
from whatsmynote.app.auth import get_supabase

console = Console()

def _get_headers() -> dict:
    session = get_supabase().auth.get_session()
    token = session.access_token if session else ""
    return {
        "Authorization": f"Bearer {token}",
        "X-Groq-Api-Key": get_groq_api_key() or ""
    }

def ensure_initial_setup() -> None:
    headers = _get_headers()
    try:
        res = requests.get(f"{API_URL}/setup/status", headers=headers)
        res.raise_for_status()
        status = res.json()
    except Exception as e:
        console.print(f"[red]Error connecting to backend: {e}[/red]")
        return

    account_count = status.get("account_count", 0)
    budget_count = status.get("budget_count", 0)
    default_account = status.get("default_account")

    accounts = []
    default_account_index = None

    if account_count == 0:
        console.print(Panel.fit("[bold]Initial account setup[/bold]\nEnter starting balances once.", border_style="cyan"))
        count = IntPrompt.ask("How many accounts do you want to set up?", default=1)
        for index in range(count):
            console.print(f"[bold cyan]Account {index + 1}/{count}[/bold cyan]")
            name = Prompt.ask("Account name")
            opening_balance = IntPrompt.ask("Opening balance", default=0)
            currency = Prompt.ask("Currency", default="INR")
            notes = Prompt.ask("Notes", default="")
            accounts.append({
                "name": name,
                "opening_balance": opening_balance,
                "currency": currency,
                "notes": notes or None,
            })
        if accounts:
            default_index = IntPrompt.ask("Which account should be default?", default=1)
            default_account_index = max(1, min(default_index, len(accounts))) - 1
    else:
        console.print(f"[dim]Found {account_count} account record(s). Skipping account setup.[/dim]")
        if default_account:
            console.print(f"[dim]Default account: {default_account}.[/dim]")

    budgets = []
    if budget_count == 0:
        if Confirm.ask("Set up budgets now?", default=True):
            console.print(Panel.fit("[bold]Initial budget setup[/bold]\nSet monthly limits.", border_style="magenta"))
            count = IntPrompt.ask("How many budgets do you want to set up?", default=0)
            for index in range(count):
                console.print(f"[bold magenta]Budget {index + 1}/{count}[/bold magenta]")
                category = Prompt.ask("Budget category", default="Overall")
                amount = IntPrompt.ask("Budget limit")
                period = Prompt.ask("Period", default="monthly")
                notes = Prompt.ask("Notes", default="")
                budgets.append({
                    "category": category,
                    "amount": amount,
                    "period": period,
                    "notes": notes or None,
                })
    else:
        console.print(f"[dim]Found {budget_count} budget record(s). Skipping budget setup.[/dim]")

    if accounts or budgets:
        payload = {
            "accounts": accounts,
            "budgets": budgets,
            "default_account_index": default_account_index
        }
        try:
            res = requests.post(f"{API_URL}/setup", json=payload, headers=headers)
            res.raise_for_status()
            console.print("[green]Setup completed successfully.[/green]")
        except Exception as e:
            console.print(f"[red]Error saving setup to backend: {e}[/red]")
