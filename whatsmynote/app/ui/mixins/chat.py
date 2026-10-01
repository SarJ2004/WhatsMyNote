import asyncio
import time

from textual import work

from whatsmynote.app.ui.present import note, problem, result_renderables

CONFIRMATION_LIFETIME = 10 * 60


class ChatMixin:
    """Sends a message to the engine and renders the reply, the balance, the
    observations, and any confirmation the engine asks for."""

    @work(group="chat")
    async def send_message(self, message: str) -> None:
        self.chatting = True
        self.set_busy(True)
        try:
            result = await asyncio.to_thread(self.app.engine.chat, message)
        finally:
            self.chatting = False
            self.set_busy(False)
        self.show_result(result)

    def show_result(self, result) -> None:
        kind = "error" if result.error else "reply"
        self.say(*result_renderables(result), kind=kind)
        if result.code == "unauthenticated":
            self.user = None
        if result.confirmation:
            self.pending = result.confirmation
            self.pending_at = time.monotonic()
        self.refresh_status()

    def confirm_pending(self) -> None:
        pending, self.pending = self.pending, None
        if time.monotonic() - self.pending_at > CONFIRMATION_LIFETIME:
            self.refresh_status()
            self.say(problem("That confirmation expired, so nothing was saved. Send the message again."),
                     kind="error")
            return
        self.refresh_status()
        self.send_confirmation(pending.token)

    def cancel_pending(self) -> None:
        self.pending = None
        self.refresh_status()
        self.say(note("Cancelled. Nothing was saved."))

    @work(group="chat")
    async def send_confirmation(self, token: str) -> None:
        self.chatting = True
        self.set_busy(True)
        try:
            result = await asyncio.to_thread(self.app.engine.confirm, token)
        finally:
            self.chatting = False
            self.set_busy(False)
        self.show_result(result)
