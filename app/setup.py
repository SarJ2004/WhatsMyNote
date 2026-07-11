"""First-run setup — accounts and budgets."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt

from db.config import SessionLocal
from db.schema import AccountRecord, BaseRecord, BudgetRecord, RecordType
from records.account_utils import get_default_account_name, set_default_account_name
from core.config import get_groq_api_key, set_groq_api_key

console = Console()


def _bootstrap_tables() -> None:
    import db.create_tables  # noqa: F401


def _count_records(model) -> int:
    db = SessionLocal()
    try:
        return db.query(model).count()
    finally:
        db.close()


def _save_account_setup(records: list[dict[str, Any]]) -> None:
    db = SessionLocal()
    try:
        for item in records:
            base_record = BaseRecord(
                record_type=RecordType.ACCOUNT, raw_text="Initial account setup"
            )
            base_record.account = AccountRecord(
                name=item["name"],
                is_default=item.get("is_default", False),
                opening_balance=item["opening_balance"],
                currency=item.get("currency"),
                notes=item.get("notes"),
            )
            db.add(base_record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _save_budget_setup(records: list[dict[str, Any]]) -> None:
    db = SessionLocal()
    try:
        for item in records:
            base_record = BaseRecord(
                record_type=RecordType.BUDGET, raw_text="Initial budget setup"
            )
            base_record.budget = BudgetRecord(
                category=item["category"],
                amount=item["amount"],
                period=item.get("period", "monthly"),
                budget_date=item.get("budget_date"),
                notes=item.get("notes"),
            )
            db.add(base_record)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _prompt_account_setup() -> None:
    console.print(
        Panel.fit(
            "[bold]Initial account setup[/bold]\nEnter starting balances once. Later runs skip this.",
            border_style="cyan",
        )
    )
    count = IntPrompt.ask("How many accounts do you want to set up?", default=1)
    records: list[dict[str, Any]] = []

    for index in range(count):
        console.print(f"[bold cyan]Account {index + 1}/{count}[/bold cyan]")
        name = Prompt.ask("Account name")
        opening_balance = IntPrompt.ask("Opening balance", default=0)
        currency = Prompt.ask("Currency", default="INR")
        notes = Prompt.ask("Notes", default="")
        records.append(
            {
                "name": name,
                "opening_balance": opening_balance,
                "current_balance": opening_balance,
                "currency": currency,
                "notes": notes or None,
            }
        )

    default_index = IntPrompt.ask(
        "Which account should be default transaction account?",
        default=1,
    )
    default_index = max(1, min(default_index, len(records))) - 1
    for index, record in enumerate(records):
        record["is_default"] = index == default_index

    _save_account_setup(records)
    console.print(f"[green]Saved {len(records)} account setup record(s).[/green]")

    db = SessionLocal()
    try:
        if records:
            set_default_account_name(db, records[default_index]["name"])
            db.commit()
            console.print(
                f"[green]Default account set to {records[default_index]['name']}.[/green]"
            )
    finally:
        db.close()


def _prompt_budget_setup() -> None:
    console.print(
        Panel.fit(
            "[bold]Initial budget setup[/bold]\nSet monthly or custom limits once. Later runs skip this. Use category [bold]Overall[/bold] for total budget.",
            border_style="magenta",
        )
    )
    count = IntPrompt.ask("How many budgets do you want to set up?", default=0)
    if count <= 0:
        console.print("[yellow]Skipped budget setup.[/yellow]")
        return

    records: list[dict[str, Any]] = []

    for index in range(count):
        console.print(f"[bold magenta]Budget {index + 1}/{count}[/bold magenta]")
        category = Prompt.ask("Budget category", default="Overall")
        amount = IntPrompt.ask("Budget limit")
        period = Prompt.ask("Period", default="monthly")
        notes = Prompt.ask("Notes", default="")
        records.append(
            {
                "category": category,
                "amount": amount,
                "period": period,
                "notes": notes or None,
            }
        )

    _save_budget_setup(records)
    console.print(f"[green]Saved {len(records)} budget record(s).[/green]")


def ensure_initial_setup() -> None:
    _bootstrap_tables()

    api_key = get_groq_api_key()
    if not api_key:
        console.print(
            Panel.fit(
                "[bold]API Key Setup[/bold]\nPlease provide your Groq API key. It will be stored locally in .env.",
                border_style="green",
            )
        )
        new_key = Prompt.ask("Groq API Key", password=True)
        if new_key:
            set_groq_api_key(new_key.strip())
            console.print("[green]API Key saved successfully.[/green]")
        else:
            console.print("[red]API Key is required to run LLM inferences. Exiting.[/red]")
            exit(1)

    account_count = _count_records(AccountRecord)
    budget_count = _count_records(BudgetRecord)

    if account_count == 0:
        _prompt_account_setup()
    else:
        db = SessionLocal()
        try:
            default_account = get_default_account_name(db)
        finally:
            db.close()

        console.print(
            f"[dim]Found {account_count} account record(s). Skipping account setup.[/dim]"
        )
        if default_account:
            console.print(f"[dim]Default account: {default_account}.[/dim]")

    if budget_count == 0:
        if Confirm.ask("Set up budgets now?", default=True):
            _prompt_budget_setup()
    else:
        console.print(
            f"[dim]Found {budget_count} budget record(s). Skipping budget setup.[/dim]"
        )
