import errno
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import httpx
from supabase import Client, create_client

from whatsmynote.app.config import SUPABASE_KEY, SUPABASE_URL, get_session_path

SESSION_FILE = get_session_path()
CALLBACK_PORT = 8080
_supabase: Client = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Refresh tokens are single use, so every refresh must reach the file
        # or the next launch starts signed out.
        _supabase.auth.on_auth_state_change(_on_auth_change)
    return _supabase


def _on_auth_change(event, session):
    if event in ("SIGNED_IN", "TOKEN_REFRESHED", "USER_UPDATED") and session:
        _save_session(session)
    elif event == "SIGNED_OUT":
        _save_session(None)


def _save_session(session):
    if session:
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
            fd = os.open(SESSION_FILE, flags, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(session.model_dump_json())
            if os.name != "nt":
                os.chmod(SESSION_FILE, 0o600)
        except Exception:
            pass
    elif os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception:
            pass


def load_session():
    supabase = get_supabase()
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if 'access_token' in data and 'refresh_token' in data:
                res = supabase.auth.set_session(
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token']
                )
                if res.user:
                    return res.user
        except Exception:
            pass
    return None


def access_token():
    try:
        session = get_supabase().auth.get_session()
    except Exception:
        return None
    return session.access_token if session else None


def login_with_password(email, password):
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    if res.user:
        _save_session(supabase.auth.get_session())
    return res.user


def signup_with_password(email, password):
    """Return (user, signed_in). Projects that confirm email return no session."""
    supabase = get_supabase()
    res = supabase.auth.sign_up({"email": email, "password": password})
    if res.session:
        _save_session(res.session)
    return res.user, bool(res.session)


def logout():
    supabase = get_supabase()
    try:
        supabase.auth.sign_out()
    finally:
        _save_session(None)
        os.environ.pop("CURRENT_USER_ID", None)


def _redirect_url():
    return f"http://localhost:{CALLBACK_PORT}"


def start_oauth(provider):
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_oauth({
        "provider": provider,
        "options": {
            "skip_browser_redirect": True,
            "redirect_to": _redirect_url()
        }
    })
    return res.url


def reset_password_for_email(email):
    supabase = get_supabase()
    supabase.auth.reset_password_for_email(
        email,
        options={"redirect_to": _redirect_url()}
    )


def update_password(new_password):
    supabase = get_supabase()
    supabase.auth.update_user({"password": new_password})
    _save_session(supabase.auth.get_session())


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WhatsMyNote</title>
<style>
body {{ margin: 0; min-height: 100vh; display: grid; place-items: center;
  font: 16px/1.5 ui-sans-serif, system-ui, sans-serif; background: #16130f; color: #f5f0e8; }}
main {{ max-width: 26rem; padding: 2rem; border: 1px solid #3a342c; border-radius: 12px; background: #221e19; }}
h1 {{ margin: 0 0 .5rem; font-size: 1.25rem; color: {accent}; }}
p {{ margin: 0; color: #b5ada3; }}
</style></head>
<body><main><h1>{title}</h1><p>{body}</p></main>{script}</body></html>"""

_FRAGMENT_SCRIPT = """<script>
if (window.location.hash) {
  window.location.replace("/?" + window.location.hash.substring(1));
}
</script>"""


def _page(title, body, accent="#fdba74", script=""):
    return _PAGE.format(title=title, body=body, accent=accent, script=script).encode("utf-8")


class _CallbackServer(HTTPServer):
    # On Windows, address reuse lets a second program bind a busy port, so a
    # clash would never be reported and the browser could reach the wrong one.
    allow_reuse_address = os.name != "nt"


def wait_for_auth_code(port=CALLBACK_PORT, cancel: threading.Event | None = None, timeout=300):
    """Wait for the browser to come back to localhost. Return the user, or None
    when the wait is cancelled or times out."""
    result = {"code": None, "access_token": None, "refresh_token": None}

    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query_params = parse_qs(urlparse(self.path).query)

            if 'code' in query_params:
                result['code'] = query_params['code'][0]
                self._send_success()
            elif 'access_token' in query_params:
                result['access_token'] = query_params['access_token'][0]
                if 'refresh_token' in query_params:
                    result['refresh_token'] = query_params['refresh_token'][0]
                self._send_success()
            elif not query_params and self.path == '/':
                self._send(200, _page(
                    "Finishing sign-in",
                    "If this page stays, the link was missing its sign-in details. "
                    "Go back to your terminal and try again.",
                    script=_FRAGMENT_SCRIPT,
                ))
            else:
                self._send(400, _page(
                    "Sign-in did not finish",
                    "The link was missing its sign-in details. Go back to your terminal and try again.",
                    accent="#fda4af",
                ))

        def _send(self, status, html):
            self.send_response(status)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)

        def _send_success(self):
            self._send(200, _page(
                "You are signed in",
                "Go back to your terminal. You can close this tab.",
            ))

        def log_message(self, format, *args):
            pass  # Silence server logs

    server = _CallbackServer(('localhost', port), OAuthCallbackHandler)
    server.timeout = 0.5
    deadline = time.monotonic() + timeout
    try:
        while not result['code'] and not result['access_token']:
            if (cancel and cancel.is_set()) or time.monotonic() > deadline:
                return None
            server.handle_request()

        supabase = get_supabase()
        if result['code']:
            supabase.auth.exchange_code_for_session({"auth_code": result['code']})
        elif result['access_token']:
            supabase.auth.set_session(
                access_token=result['access_token'],
                refresh_token=result['refresh_token']
            )

        session = supabase.auth.get_session()
        _save_session(session)
        if session and session.user:
            return session.user
        return None
    finally:
        server.server_close()


def auth_error_sentence(error) -> str:
    """One plain sentence for a failed sign-in step. Never the raw exception."""
    if isinstance(error, OSError) and error.errno in (errno.EADDRINUSE, 10048):
        return (f"Another program is using port {CALLBACK_PORT}, so the browser cannot "
                "finish signing in. Close it and try again.")
    if isinstance(error, httpx.TransportError):
        return "Could not reach the sign-in service. Check your internet connection."
    text = str(error).lower()
    if "invalid login credentials" in text:
        return "That email and password do not match. Try again, or pick Forgot password."
    if "email not confirmed" in text:
        return "Confirm your email first. Open the link we sent you, then sign in."
    if "already registered" in text or "already been registered" in text:
        return "That email already has an account. Sign in instead."
    if "password" in text and ("at least" in text or "weak" in text or "short" in text):
        return "Choose a stronger password, at least 6 characters long."
    if "rate limit" in text or "too many" in text:
        return "Too many attempts. Wait a minute, then try again."
    if "email" in text and ("invalid" in text or "validate" in text):
        return "That email address does not look right. Check it and try again."
    return "That did not work. Try again in a moment."


class SupabaseAuth:
    """The sign-in operations the screen uses. Tests pass their own."""

    restore = staticmethod(load_session)
    sign_in = staticmethod(login_with_password)
    sign_up = staticmethod(signup_with_password)
    sign_out = staticmethod(logout)
    browser_url = staticmethod(start_oauth)
    send_reset = staticmethod(reset_password_for_email)
    set_password = staticmethod(update_password)
    access_token = staticmethod(access_token)

    @staticmethod
    def wait_for_browser(cancel):
        return wait_for_auth_code(cancel=cancel)
