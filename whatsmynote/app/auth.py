import os
import json
import webbrowser
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
from supabase import create_client, Client

from whatsmynote.app.config import get_session_path, SUPABASE_URL, SUPABASE_KEY

SESSION_FILE = get_session_path()
_supabase: Client = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

def _save_session(session):
    if session:
        try:
            with open(SESSION_FILE, "w") as f:
                f.write(session.model_dump_json())
        except Exception:
            pass
    else:
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except Exception:
                pass

def load_session():
    supabase = get_supabase()
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
            if 'access_token' in data and 'refresh_token' in data:
                res = supabase.auth.set_session(
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token']
                )
                if res.user:
                    os.environ["CURRENT_USER_ID"] = res.user.id
                    return res.user
        except Exception:
            pass
    return None

def login_with_password(email, password):
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
    if res.user:
        _save_session(supabase.auth.get_session())
        os.environ["CURRENT_USER_ID"] = res.user.id
    return res.user

def signup_with_password(email, password):
    supabase = get_supabase()
    res = supabase.auth.sign_up({"email": email, "password": password})
    return res.user

def start_oauth(provider):
    supabase = get_supabase()
    res = supabase.auth.sign_in_with_oauth({
        "provider": provider,
        "options": {
            "skip_browser_redirect": True,
            "redirect_to": "http://localhost:8080"
        }
    })
    return res.url

def reset_password_for_email(email):
    supabase = get_supabase()
    supabase.auth.reset_password_for_email(
        email, 
        options={"redirect_to": "http://localhost:8080"}
    )

def update_password(new_password):
    supabase = get_supabase()
    supabase.auth.update_user({"password": new_password})
    _save_session(supabase.auth.get_session())

def wait_for_auth_code(port=8080):
    result = {"code": None, "access_token": None, "refresh_token": None}
    
    class OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            
            if 'code' in query_params:
                result['code'] = query_params['code'][0]
                self._send_success()
            elif 'access_token' in query_params:
                result['access_token'] = query_params['access_token'][0]
                if 'refresh_token' in query_params:
                    result['refresh_token'] = query_params['refresh_token'][0]
                self._send_success()
            elif not query_params and self.path == '/':
                html = """
                <html><body>
                <script>
                if (window.location.hash) {
                    window.location.href = "/?" + window.location.hash.substring(1);
                } else {
                    document.body.innerHTML = "<h1>Action Failed!</h1><p>Missing authentication parameters.</p>";
                }
                </script>
                </body></html>
                """
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Action Failed!</h1><p>Missing code.</p></body></html>")
                
        def _send_success(self):
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            success_html = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Action Successful</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-950 h-screen flex flex-col items-center justify-center font-sans selection:bg-green-500/30 relative">
                <div class="bg-gray-900 p-10 rounded-3xl shadow-2xl text-center max-w-md w-full border border-gray-800">
                    <h1 class="text-3xl font-extrabold text-white mb-2">Success!</h1>
                    <p class="text-gray-400 mb-8">Action completed successfully. You can close this tab.</p>
                </div>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode('utf-8'))

        def log_message(self, format, *args):
            pass # Silence server logs

    server = HTTPServer(('localhost', port), OAuthCallbackHandler)
    try:
        while not result['code'] and not result['access_token']:
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
            os.environ["CURRENT_USER_ID"] = session.user.id
            return session.user
        return None
    finally:
        server.server_close()
