import webbrowser
from textual import work
from textual.widgets import RichLog, Input

from whatsmynote.app.auth import (
    login_with_password, signup_with_password, 
    start_oauth, wait_for_auth_code,
    reset_password_for_email, update_password,
    logout
)

class AuthMixin:
    """Mixin for authentication flows in the TUI."""

    @work(thread=True)
    def do_login(self, email, password):
        log = self.query_one("#chat-log", RichLog)
        try:
            user = login_with_password(email, password)
            self.app.call_from_thread(log.write, f"[#dddddd]logged in successfully as {user.email}[/#dddddd]")
            self.app.call_from_thread(self.update_user_label)
            self.check_onboarding_status()
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]login failed: {str(e)}[/#ffaa55]")

    @work(thread=True)
    def do_signup(self, email, password):
        log = self.query_one("#chat-log", RichLog)
        try:
            signup_with_password(email, password)
            self.app.call_from_thread(log.write, "[#dddddd]sign up successful! you can now log in.[/#dddddd]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]sign up failed: {str(e)}[/#ffaa55]")

    @work(thread=True)
    def do_oauth(self, provider):
        log = self.query_one("#chat-log", RichLog)
        try:
            url = start_oauth(provider)
            webbrowser.open(url)
            self.app.call_from_thread(log.write, "[#888888]waiting for authentication code from browser...[/#888888]")
            user = wait_for_auth_code()
            if user:
                self.app.call_from_thread(log.write, f"[#dddddd]successfully authenticated as {user.email}![/#dddddd]")
                self.app.call_from_thread(self.update_user_label)
                self.check_onboarding_status()
            else:
                self.app.call_from_thread(log.write, "[#ffaa55]authentication failed: no code received.[/#ffaa55]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]oauth failed: {str(e)}[/#ffaa55]")

    @work(thread=True)
    def do_password_reset(self, email):
        log = self.query_one("#chat-log", RichLog)
        try:
            reset_password_for_email(email)
            self.app.call_from_thread(log.write, "[#888888]password reset email sent. check your inbox and click the link...[/#888888]")
            
            user = wait_for_auth_code()
            if user:
                self.app.call_from_thread(self.prompt_new_password)
            else:
                self.app.call_from_thread(log.write, "[#ffaa55]password reset failed: no code received.[/#ffaa55]")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]password reset error: {str(e)}[/#ffaa55]")
            
    def prompt_new_password(self):
        log = self.query_one("#chat-log", RichLog)
        inp = self.query_one("#main-input", Input)
        log.write("Enter new password:")
        inp.password = True
        self.set_state("AUTH_FORGOT_NEW_PASS")

    @work(thread=True)
    def do_password_update(self, new_password):
        log = self.query_one("#chat-log", RichLog)
        try:
            update_password(new_password)
            self.app.call_from_thread(log.write, "[#dddddd]password updated successfully! you are now logged in.[/#dddddd]")
            self.app.call_from_thread(self.update_user_label)
            self.check_onboarding_status()
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]password update failed: {str(e)}[/#ffaa55]")
            
    @work(thread=True)
    def do_logout(self):
        log = self.query_one("#chat-log", RichLog)
        try:
            logout()
            self.app.call_from_thread(log.write, "[#dddddd]logged out successfully.[/#dddddd]")
            self.app.call_from_thread(self.update_user_label)
        except Exception as e:
            self.app.call_from_thread(log.write, f"[#ffaa55]logout failed: {str(e)}[/#ffaa55]")
