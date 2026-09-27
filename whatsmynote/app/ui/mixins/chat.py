import requests
from textual import work
from textual.widgets import RichLog

from whatsmynote.app.auth import get_supabase
from whatsmynote.app.config import API_URL
from whatsmynote.app.ui.errors import sentence_for


class ChatMixin:
    """Posts a message to the engine and renders the result or an error sentence.

    The client sends the message and the session token. It does not send a state
    blob, and it does not send a model key.
    """

    @work(thread=True)
    def do_chat(self, message: str):
        log = self.query_one("#chat-log", RichLog)
        session = get_supabase().auth.get_session()
        token = session.access_token if session else ""
        headers = {"Authorization": f"Bearer {token}"}

        indicator = self.query_one("#thinking-indicator")
        self.app.call_from_thread(indicator.start)
        try:
            response = requests.post(
                f"{API_URL}/chat", json={"message": message}, headers=headers
            )
            body = response.json()
        except Exception:
            self.app.call_from_thread(indicator.stop)
            self.app.call_from_thread(
                log.write, "[#ffaa55]The server did not answer. Try again.[/#ffaa55]"
            )
            return
        self.app.call_from_thread(indicator.stop)
        self.app.call_from_thread(self.render_backend_response, body, response.ok)

    def render_backend_response(self, body: dict, ok: bool):
        log = self.query_one("#chat-log", RichLog)
        if not ok or (isinstance(body, dict) and body.get("code")):
            log.write(f"[#ffaa55]{sentence_for(body)}[/#ffaa55]")
            self.set_state("IDLE")
            return
        if isinstance(body, dict) and "balance" in body:
            log.write(f"[#dddddd]Balance: {body['balance']}[/#dddddd]")
        elif isinstance(body, dict) and body.get("message"):
            log.write(f"[#dddddd]{body['message']}[/#dddddd]")
        else:
            log.write(f"[#dddddd]{body}[/#dddddd]")
        self.set_state("IDLE")
