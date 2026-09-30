import asyncio
import webbrowser

from textual import work

from whatsmynote.app.ui.present import display_name, note, problem, success


class AuthMixin:
    """Sign-in flows. The password goes only to the sign-in service."""

    @work(exclusive=True, group="session")
    async def restore_session(self) -> None:
        try:
            user = await asyncio.to_thread(self.app.auth.restore)
        except Exception:
            user = None
        self.checking = False
        if self.user is None:
            self.user = user
        self.refresh_status()
        if self.user:
            self.check_accounts()

    def signed_in(self, user) -> None:
        self.user = user
        self.refresh_status()
        self.say(success(f"Signed in as {getattr(user, 'email', '') or display_name(user)}."))
        self.check_accounts()

    @work(exclusive=True, group="dialog")
    async def login_flow(self) -> None:
        from whatsmynote.app.ui.dialogs import EmailForm, SignInMenu

        if self.user:
            self.say(note("You are already signed in. Type /logout first to switch accounts."))
            return
        choice = await self.app.push_screen_wait(SignInMenu())
        if choice in ("google", "github"):
            await self._browser_sign_in(choice)
        elif choice in ("email", "signup"):
            outcome = await self.app.push_screen_wait(
                EmailForm(self.app.auth, mode="signup" if choice == "signup" else "signin")
            )
            if not outcome:
                self.say(note("Sign-in cancelled."))
            elif outcome["signed_in"]:
                self.signed_in(outcome["user"])
            else:
                self.say(success(f"Account created for {outcome['email']}."))
                self.say(note("Open the confirmation link we emailed you, then type /login to sign in."))
        elif choice == "reset":
            await self._reset_password()
        else:
            self.say(note("Sign-in cancelled."))

    async def _browser_sign_in(self, provider: str) -> None:
        from whatsmynote.app.auth import auth_error_sentence
        from whatsmynote.app.ui.dialogs import BrowserWait

        name = "GitHub" if provider == "github" else "Google"
        try:
            url = await asyncio.to_thread(self.app.auth.browser_url, provider)
        except Exception as error:
            self.say(problem(auth_error_sentence(error)))
            return
        await asyncio.to_thread(webbrowser.open, url)
        outcome = await self.app.push_screen_wait(BrowserWait(
            f"Continue with {name}",
            f"Your browser is open at {name}. Sign in there, then come back here.",
            self.app.auth.wait_for_browser,
            link=url,
        ))
        if not outcome:
            self.say(note("Sign-in cancelled."))
        elif outcome.get("error"):
            self.say(problem(outcome["error"]))
        elif outcome.get("user"):
            self.signed_in(outcome["user"])
        else:
            self.say(problem(f"{name} did not finish signing you in. Type /login to try again."))

    async def _reset_password(self) -> None:
        from whatsmynote.app.ui.dialogs import BrowserWait, NewPasswordForm, ResetForm

        email = await self.app.push_screen_wait(ResetForm(self.app.auth))
        if not email:
            self.say(note("Password reset cancelled."))
            return
        outcome = await self.app.push_screen_wait(BrowserWait(
            "Check your email",
            f"We sent a reset link to {email}. Open it on this computer, then come back here.",
            self.app.auth.wait_for_browser,
        ))
        if not outcome:
            self.say(note("Password reset cancelled. The emailed link still works if you type /login again."))
            return
        if outcome.get("error") or not outcome.get("user"):
            self.say(problem(outcome.get("error") or "The reset link did not come back. Type /login to try again."))
            return
        if await self.app.push_screen_wait(NewPasswordForm(self.app.auth)):
            self.say(success("Password changed."))
        else:
            self.say(note("Password not changed. You are signed in with the emailed link."))
        self.signed_in(outcome["user"])

    @work(exclusive=True, group="dialog")
    async def logout_flow(self) -> None:
        if not self.user:
            self.say(note("You are not signed in."))
            return
        try:
            await asyncio.to_thread(self.app.auth.sign_out)
        except Exception:
            pass  # The local session is removed either way.
        self.user = None
        self.pending = None
        self.refresh_status()
        self.say(success("Signed out of this computer."))
