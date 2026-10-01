import asyncio

from textual import work

from whatsmynote.app.ui.constants import EXAMPLES
from whatsmynote.app.ui.present import balances_table, note, problem, success


class OnboardingMixin:
    """Accounts go through the engine. The terminal holds no finance logic."""

    @work(exclusive=True, group="accounts")
    async def check_accounts(self) -> None:
        balances = await asyncio.to_thread(self.app.engine.balances)
        if balances.error:
            self.say(problem(balances.error), kind="error")
            if balances.code == "unauthenticated":
                self.user = None
                self.refresh_status()
            return
        if not balances.rows:
            await self._add_account(first=True)
        if not self.app.keys.load().key:
            await self.edit_key(first=True)

    @work(exclusive=True, group="dialog")
    async def account_flow(self) -> None:
        await self._add_account(first=False)

    async def _add_account(self, first: bool) -> None:
        from whatsmynote.app.ui.dialogs import AccountForm

        name = await self.app.push_screen_wait(AccountForm(self.app.engine, first=first))
        if name:
            self.say(success(f"{name} is ready. Write what happened, like: {EXAMPLES[0]}"))
        elif first:
            self.say(note("No account yet. Add one any time with /account."))
        else:
            self.say(note("No account added."))

    @work(exclusive=True, group="accounts")
    async def show_balances(self) -> None:
        self.set_busy(True)
        try:
            balances = await asyncio.to_thread(self.app.engine.balances)
        finally:
            self.set_busy(False)
        if balances.error:
            self.say(problem(balances.error), kind="error")
        else:
            self.say(balances_table(balances.rows), kind="card")
