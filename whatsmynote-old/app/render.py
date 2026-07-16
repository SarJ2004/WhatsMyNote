"""Rich output rendering for CLI results."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


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


def _render_analytics_chart(rows: list[dict[str, Any]], chart_config: dict[str, Any]) -> None | str:
    chart_type = chart_config.get("chart_type")
    if not chart_type or chart_type == "none":
        return None

    x_col = chart_config.get("x_axis")
    y_col = chart_config.get("y_axis")
    if not x_col or not y_col:
        return None
        
    title = chart_config.get("title") or "Analytics Chart"
    color = chart_config.get("color")

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
            # Fallback if termcharts fails
            chart_type = "bar"

    import plotext as plt
    plt.clf()

    if chart_type == "line":
        plt.date_form("Y-m-d")
        
        # Sort by date
        sorted_rows = sorted(rows, key=lambda row: str(row.get(x_col, "")))
        labels = [str(row.get(x_col, "")) for row in sorted_rows]
        values = [float(row.get(y_col) or 0) for row in sorted_rows]
        
        plt.plot(labels, values, marker="dot")
    else:
        # Sort by value for bar chart
        top_rows = sorted(rows, key=lambda row: float(row.get(y_col) or 0), reverse=True)[:15]
        labels = [str(row.get(x_col, "")) for row in top_rows]
        values = [float(row.get(y_col) or 0) for row in top_rows]
        
        if chart_type == "scatter":
            plt.scatter(labels, values)
        else:
            plt.bar(labels, values, orientation="horizontal")
            
    plt.title(title)

    if color:
        try:
            if color == "diverse":
                plt.colorless() # plotext does not strictly have diverse, but we can set multiple colors. Actually plotext uses diverse colors automatically if we don't set color.
            else:
                plt.color(color)
        except Exception:
            pass

    plt.plotsize(60, 20)
    plt.theme("clear")
    
    # Render and encode safely to avoid Windows cp1252 crash
    try:
        chart_str = plt.build()
        return chart_str
    except Exception:
        plt.theme("pro") # Fallback to a simpler theme
        return plt.build()


def _render_budget_alerts(alerts: list[str]) -> None:
    if not alerts:
        return

    table = Table(title="Budget Alerts", header_style="bold yellow")
    table.add_column("Alert")
    for alert in alerts:
        table.add_row(alert)
    console.print(table)


def render_result(state: dict[str, Any]) -> None:
    """Render the graph output state to the CLI."""
    if state.get("error"):
        console.print(
            Panel.fit(
                f"[bold red]Error[/bold red]\n{state['error']}", border_style="red"
            )
        )
        return

    analytics_sql = state.get("analytics_sql")
    analytics_review = state.get("analytics_review")
    query_result = state.get("query_result")
    answer = state.get("answer")
    budget_alerts = state.get("budget_alerts") or []

    if analytics_sql:
        console.print(Panel.fit(analytics_sql, title="SQL", border_style="dim"))

    if analytics_review:
        console.print(
            Panel.fit(str(analytics_review), title="SQL Review", border_style="cyan")
        )

    if budget_alerts:
        _render_budget_alerts(list(dict.fromkeys(budget_alerts)))

    chart_config = state.get("chart_config")

    if query_result is not None:
        if isinstance(query_result, list):
            if query_result and isinstance(query_result[0], dict) and chart_config:
                chart = _render_analytics_chart(query_result, chart_config)
                if chart:
                    chart_type = chart_config.get("chart_type")
                    if chart_type in ["pie", "donut"]:
                        # termcharts returns raw ANSI strings. We MUST parse them via Text.from_ansi
                        # otherwise Rich's markup parser gets confused and prints literal [31m tags.
                        from rich.text import Text
                        console.print(f"\n[bold green]Analytics Chart:[/bold green] {chart_config.get('title', '')}")
                        console.print(Text.from_ansi(chart))
                    else:
                        console.print(
                            Panel.fit(chart, title="Analytics Chart", border_style="green")
                        )
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

    # Check for successful operations
    if state.get("saved_record_ids"):
        count = len(state["saved_record_ids"])
        console.print(
            Panel.fit(f"Successfully created {count} record(s).", title="Result", border_style="green")
        )
        return

    if state.get("updated_record_id"):
        console.print(
            Panel.fit(f"Record #{state['updated_record_id']} updated successfully.", title="Result", border_style="green")
        )
        return

    if state.get("deleted_record_id"):
        console.print(
            Panel.fit(f"Record #{state['deleted_record_id']} deleted successfully.", title="Result", border_style="green")
        )
        return

    console.print(
        Panel.fit("Operation completed.", title="Result", border_style="green")
    )
