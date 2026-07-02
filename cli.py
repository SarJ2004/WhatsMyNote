from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from db.config import SessionLocal
from db.schema import AccountRecord, BaseRecord, BudgetRecord, RecordType
from graph import compiled_graph


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
            base_record = BaseRecord(record_type=RecordType.ACCOUNT, raw_text="Initial account setup")
            base_record.account = AccountRecord(
                name=item["name"],
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
            base_record = BaseRecord(record_type=RecordType.BUDGET, raw_text="Initial budget setup")
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
    console.print(Panel.fit("[bold]Initial account setup[/bold]\nEnter starting balances once. Later runs skip this.", border_style="cyan"))
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
                "currency": currency,
                "notes": notes or None,
            }
        )

    _save_account_setup(records)
    console.print(f"[green]Saved {len(records)} account setup record(s).[/green]")


def _prompt_budget_setup() -> None:
    console.print(Panel.fit("[bold]Initial budget setup[/bold]\nSet monthly or custom limits once. Later runs skip this.", border_style="magenta"))
    count = IntPrompt.ask("How many budgets do you want to set up?", default=0)
    if count <= 0:
        console.print("[yellow]Skipped budget setup.[/yellow]")
        return

    records: list[dict[str, Any]] = []

    for index in range(count):
        console.print(f"[bold magenta]Budget {index + 1}/{count}[/bold magenta]")
        category = Prompt.ask("Budget category")
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

    account_count = _count_records(AccountRecord)
    budget_count = _count_records(BudgetRecord)

    if account_count == 0:
        _prompt_account_setup()
    else:
        console.print(f"[dim]Found {account_count} account record(s). Skipping account setup.[/dim]")

    if budget_count == 0:
        if Confirm.ask("Set up budgets now?", default=True):
            _prompt_budget_setup()
    else:
        console.print(f"[dim]Found {budget_count} budget record(s). Skipping budget setup.[/dim]")


def _normalize_item(item: Any) -> Any:
    if hasattr(item, "__dict__"):
        return {
            key: value
            for key, value in vars(item).items()
            if not key.startswith("_") and key != "record"
        }
    return item


def _render_table_from_rows(rows: list[Any]) -> None:
    if not rows:
        console.print(Panel("No rows.", title="Result", border_style="yellow"))
        return

    normalized_rows = [_normalize_item(row) for row in rows]
    first_row = normalized_rows[0]
    if not isinstance(first_row, dict):
        console.print(Panel(str(rows), title="Result", border_style="cyan"))
        return

    table = Table(title="Result", show_lines=False, header_style="bold cyan")
    for column in first_row.keys():
        table.add_column(str(column), overflow="fold")

    for row in normalized_rows:
        table.add_row(*[str(row.get(column, "")) for column in first_row.keys()])

    console.print(table)


def render_result(state: dict[str, Any]) -> None:
    if state.get("error"):
        console.print(Panel.fit(f"[bold red]Error[/bold red]\n{state['error']}", border_style="red"))
        return

    query_result = state.get("query_result")
    answer = state.get("answer")

    if query_result is not None:
        if isinstance(query_result, list):
            _render_table_from_rows(query_result)
            return

        if isinstance(query_result, dict):
            table = Table(title="Result", header_style="bold cyan")
            table.add_column("Key")
            table.add_column("Value")
            for key, value in query_result.items():
                table.add_row(str(key), str(value))
            console.print(table)
            return

        console.print(Panel.fit(str(query_result), title="Result", border_style="cyan"))
        return

    if answer:
        console.print(Panel.fit(answer, title="Result", border_style="green"))
        return

    console.print(Panel.fit("Operation completed.", title="Result", border_style="green"))


def run_chat_loop() -> None:
    console.print(
        Panel.fit(
            "[bold]WhatsMyNote CLI[/bold]\nType finance messages. Use [bold]exit[/bold] or [bold]quit[/bold] to stop.",
            border_style="blue",
        )
    )

    while True:
        message = Prompt.ask("[bold blue]You[/bold blue]")
        if message.strip().lower() in {"exit", "quit", "q"}:
            console.print("[dim]Bye.[/dim]")
            break

        state = compiled_graph.invoke({"raw_text": message})
        render_result(state)


def main() -> None:
    ensure_initial_setup()
    run_chat_loop()


if __name__ == "__main__":
    main()