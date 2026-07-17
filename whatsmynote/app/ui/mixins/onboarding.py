import requests
from textual import work
from textual.widgets import RichLog

from whatsmynote.app.auth import get_supabase
from whatsmynote.app.config import API_URL

class OnboardingMixin:
    """Mixin for onboarding flows in the TUI."""

    @work(thread=True)
    def check_onboarding_status(self):
        log = self.query_one("#chat-log", RichLog)
        session = get_supabase().auth.get_session()
        token = session.access_token if session else ""
        headers = {"Authorization": f"Bearer {token}"}
        try:
            res = requests.get(f"{API_URL}/setup/status", headers=headers)
            res.raise_for_status()
            data = res.json()
            if data.get("account_count", 0) == 0:
                self.app.call_from_thread(self.start_onboarding)
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]Failed to check setup status: {e}[/#ffaa55]")
            
    def start_onboarding(self):
        log = self.query_one("#chat-log", RichLog)
        self.query_one("#startup-container").display = False
        log.display = True
        self._chat_started = True
        self.onboarding_data = {
            "accounts": [],
            "budgets": [],
            "target_accounts": 1,
            "target_budgets": 0,
            "current_index": 1,
            "default_account_index": 0,
            "current_account": {},
            "current_budget": {}
        }
        self.set_state("OB_ACC_COUNT")
        log.write("\n[#dddddd bold]Welcome to WhatsMyNote![/#dddddd bold] Let's set up your profile.")
        log.write("How many accounts do you want to start with? [Default: 1]")

    @work(thread=True)
    def do_onboarding_setup(self):
        log = self.query_one("#chat-log", RichLog)
        session = get_supabase().auth.get_session()
        token = session.access_token if session else ""
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "accounts": self.onboarding_data.get("accounts", []),
            "budgets": self.onboarding_data.get("budgets", []),
            "default_account_index": self.onboarding_data.get("default_account_index", 0)
        }
        try:
            res = requests.post(f"{API_URL}/setup", json=payload, headers=headers)
            res.raise_for_status()
            self.app.call_from_thread(log.write, "[#dddddd]Setup complete! You can now start using WhatsMyNote.[/#dddddd]")
            self.app.call_from_thread(self.set_state, "IDLE")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]Failed to save setup: {e}[/#ffaa55]")
            self.app.call_from_thread(self.set_state, "IDLE")
