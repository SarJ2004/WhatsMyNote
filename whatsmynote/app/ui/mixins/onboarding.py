import requests
from textual import work
from textual.widgets import RichLog

from whatsmynote.app.auth import get_supabase
from whatsmynote.app.config import API_URL
from whatsmynote.app.ui.errors import sentence_for


class OnboardingMixin:
    """Creates the first account through the engine. The terminal holds no
    finance logic of its own."""

    def _headers(self):
        session = get_supabase().auth.get_session()
        token = session.access_token if session else ""
        return {"Authorization": f"Bearer {token}"}

    @work(thread=True)
    def check_onboarding_status(self):
        log = self.query_one("#chat-log", RichLog)
        try:
            res = requests.get(f"{API_URL}/balances", headers=self._headers())
            if res.status_code == 401:
                return
            res.raise_for_status()
            balances = res.json().get("balances") or []
            if not balances:
                self.app.call_from_thread(self.start_onboarding)
        except Exception:
            self.app.call_from_thread(
                log.write, "[#ffaa55]Could not read your accounts.[/#ffaa55]"
            )

    def start_onboarding(self):
        log = self.query_one("#chat-log", RichLog)
        self.query_one("#startup-container").display = False
        log.display = True
        self._chat_started = True
        self.onboarding_data = {"name": None}
        self.set_state("OB_ACC_NAME")
        log.write("\n[#dddddd bold]Welcome to WhatsMyNote.[/#dddddd bold]")
        log.write("Name your first account. [Default: Cash]")

    @work(thread=True)
    def do_onboarding_setup(self):
        log = self.query_one("#chat-log", RichLog)
        account = self.onboarding_data
        payload = {
            "name": account.get("name") or "Cash",
            "currency": "INR",
            "opening_balance": account.get("opening_balance") or 0,
        }
        try:
            res = requests.post(
                f"{API_URL}/accounts", json=payload, headers=self._headers()
            )
            if not res.ok:
                sentence = sentence_for(res.json())
                self.app.call_from_thread(log.write, f"[#ffaa55]{sentence}[/#ffaa55]")
                self.app.call_from_thread(self.set_state, "IDLE")
                return
            self.app.call_from_thread(
                log.write, "[#dddddd]Account ready. You can log money now.[/#dddddd]"
            )
            self.app.call_from_thread(self.set_state, "IDLE")
        except Exception:
            self.app.call_from_thread(
                log.write, "[#ffaa55]Could not save the account.[/#ffaa55]"
            )
            self.app.call_from_thread(self.set_state, "IDLE")
