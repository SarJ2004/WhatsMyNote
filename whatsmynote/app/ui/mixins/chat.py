import os
import requests
from textual import work
from textual.widgets import RichLog
from rich.table import Table
from rich.text import Text
from rich import box
from rich.panel import Panel

from whatsmynote.app.auth import get_supabase
from whatsmynote.app.config import get_groq_api_key, API_URL

class ChatMixin:
    """Mixin for core chat and data visualization flows in the TUI."""

    @work(thread=True)
    def do_chat(self, message: str, is_selection: bool = False):
        log = self.query_one("#chat-log", RichLog)
        
        if not is_selection:
            self.app_state["raw_text"] = message

        session = get_supabase().auth.get_session()
        token = session.access_token if session else ""
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Groq-Api-Key": get_groq_api_key() or ""
        }
        payload = {"message": self.app_state.get("raw_text", ""), "state": self.app_state}

        indicator = self.query_one("#thinking-indicator")
        self.app.call_from_thread(indicator.start)

        try:
            response = requests.post(f"{API_URL}/chat", json=payload, headers=headers)
            response.raise_for_status()
            self.app_state = response.json().get("state", {})
            self.app.call_from_thread(indicator.stop)
            self.app.call_from_thread(self.render_backend_response, self.app_state)
        except Exception as e:
            self.app.call_from_thread(indicator.stop)
            if os.environ.get("ENV") == "dev":
                self.app.call_from_thread(log.write, f"[#ffaa55]backend error: {e}[/#ffaa55]")
            else:
                self.app.call_from_thread(log.write, "[#ffaa55]We're sorry, but the server encountered an unexpected error. Please try again later.[/#ffaa55]")

    def render_backend_response(self, state: dict):
        log = self.query_one("#chat-log", RichLog)
        
        answer = state.get("answer")
        query_result = state.get("query_result")
        budget_alerts = state.get("budget_alerts") or []
        chart_config = state.get("chart_config")
        analytics_sql = state.get("analytics_sql")
        analytics_review = state.get("analytics_review")

        is_dev = os.environ.get("ENV") == "dev"

        if is_dev and analytics_sql:
            log.write(Panel.fit(analytics_sql, title="SQL", border_style="dim"))

        if is_dev and analytics_review:
            log.write(Panel.fit(str(analytics_review), title="SQL Review", border_style="cyan"))

        if state.get("error"):
            log.write(f"[#ffaa55]Error: {state['error']}[/#ffaa55]")
            return

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
            
        if state.get("awaiting_confirmation"):
            self.set_state("AWAITING_CONFIRMATION")
        elif state.get("awaiting_update_details"):
            self.set_state("AWAITING_UPDATE_DETAILS")
        elif not state.get("awaiting_selection"):
            self.set_state("IDLE")

        # HITL
        if state.get("awaiting_selection") and state.get("search_results"):
            self.current_search_results = state["search_results"]
            intent = state.get("intent", "update")
            mode = "multi" if intent == "delete" else "single"
            
            def selection_callback(selected_ids: list):
                if not selected_ids:
                    log.write("[#888888]selection cancelled.[/#888888]")
                    self.set_state("IDLE")
                    return
                
                self.app_state["awaiting_selection"] = False
                if mode == "single":
                    self.app_state["selected_record_id"] = selected_ids[0]
                    self.app_state["selected_record_ids"] = None
                    self.app_state["raw_text"] = f"select {selected_ids[0]}"
                else:
                    self.app_state["selected_record_id"] = None
                    self.app_state["selected_record_ids"] = selected_ids
                    self.app_state["raw_text"] = f"select {','.join(map(str, selected_ids))}"
                
                self.set_state("IDLE")
                self.do_chat("", is_selection=True)

            from whatsmynote.app.ui.screens import SelectionModal
            self.app.push_screen(SelectionModal(self.current_search_results, mode=mode), selection_callback)

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
            sorted_rows = sorted(rows, key=lambda row: str(row.get(x_col, "")))
            labels = [str(row.get(x_col, "")) for row in sorted_rows]
            values = [float(row.get(y_col) or 0) for row in sorted_rows]
            x_ticks = list(range(len(labels)))
            plt.plot(x_ticks, values, marker="dot")
            plt.xticks(x_ticks, labels)
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
