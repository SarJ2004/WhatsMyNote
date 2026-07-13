from rich.console import Console
from rich.prompt import Prompt
from supabase import create_client, Client
import os
import json
import webbrowser
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

console = Console()
from whatsmynote.app.config import get_session_path, SUPABASE_URL, SUPABASE_KEY
SESSION_FILE = get_session_path()

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

def _load_session():
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
                return res.user
        except Exception:
            pass
    return None

_supabase: Client = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = SUPABASE_URL
        key = SUPABASE_KEY
        if not url or not key:
            console.print("[red]Supabase URL and Key must be set in .env[/red]")
            exit(1)
        _supabase = create_client(url, key)
    return _supabase

def _wait_for_auth_code(port=8080):
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
    
    <div class="bg-gray-900 p-10 rounded-3xl shadow-2xl text-center max-w-md w-full border border-gray-800 transform transition-all hover:scale-105 duration-300 relative z-10">
        
        <!-- Logo loaded directly from your GitHub repo -->
        <img src="https://raw.githubusercontent.com/SarJ2004/WhatsMyNote/main/docs/assets/logo.png" alt="WhatsMyNote Logo" class="h-20 w-auto mx-auto mb-6 drop-shadow-2xl" onerror="this.style.display='none'">

        <div class="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6 shadow-[0_0_30px_rgba(34,197,94,0.2)]">
            <div class="w-14 h-14 bg-green-500 rounded-full flex items-center justify-center shadow-lg shadow-green-500/40">
                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3.5" d="M5 13l4 4L19 7"></path></svg>
            </div>
        </div>
        
        <h1 class="text-3xl font-extrabold text-white mb-2 tracking-tight">Success!</h1>
        <p class="text-gray-400 mb-8 text-md font-medium">Action completed successfully.</p>
        
        <div class="bg-gray-950/50 rounded-2xl p-5 mb-8 border border-green-900/30 shadow-inner">
            <p class="text-green-400 font-bold text-lg tracking-wider uppercase mb-1">Safe to close</p>
            <p class="text-gray-500 text-sm">You can now close this tab and return to the terminal.</p>
        </div>

        <p class="text-gray-300 font-semibold text-lg">Thank you for using WhatsMyNote!</p>
    </div>

    <!-- Branding Footer -->
    <div class="absolute bottom-8 text-center opacity-40">
        <p class="text-gray-400 text-xs tracking-[0.3em] uppercase font-bold">WhatsMyNote Open Source</p>
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
        return result
    finally:
        server.server_close()

def ensure_authenticated():
    supabase = get_supabase()
    
    # Try restoring previous session
    user = _load_session()
    if user:
        os.environ["CURRENT_USER_ID"] = user.id
        console.print(f"[green]Restored session for {user.email}[/green]")
        return
        
    console.print("\n[bold blue]WhatsMyNote - Supabase Authentication[/bold blue]")
    while True:
        action = Prompt.ask("Do you want to (L)og in, (S)ign up, (F)orgot Password, or (O)Auth [Google/GitHub]?", choices=["l", "s", "f", "o", "q"], default="l").lower()
        if action == "q":
            exit(0)
            
        if action == "f":
            email = Prompt.ask("Email for password reset")
            try:
                supabase.auth.reset_password_for_email(
                    email, 
                    options={"redirect_to": "http://localhost:8080"}
                )
                console.print("[dim]Password reset email sent. Please check your inbox and click the link...[/dim]")
                
                auth_result = _wait_for_auth_code()
                if auth_result['code']:
                    supabase.auth.exchange_code_for_session({"auth_code": auth_result['code']})
                elif auth_result['access_token']:
                    supabase.auth.set_session(
                        access_token=auth_result['access_token'],
                        refresh_token=auth_result['refresh_token']
                    )
                
                if auth_result['code'] or auth_result['access_token']:
                    new_password = Prompt.ask("Enter new password", password=True)
                    supabase.auth.update_user({"password": new_password})
                    console.print("[green]Password updated successfully! You are now logged in.[/green]")
                    break
                else:
                    console.print("[red]Password reset failed: No code received.[/red]")
            except Exception as e:
                console.print(f"[red]Password reset error: {str(e)}[/red]")
            continue
            
        if action == "o":
            provider = Prompt.ask("Which provider?", choices=["google", "github"], default="google").lower()
            try:
                res = supabase.auth.sign_in_with_oauth({
                    "provider": provider,
                    "options": {
                        "skip_browser_redirect": True,
                        "redirect_to": "http://localhost:8080"
                    }
                })
                
                console.print(f"[dim]Opening browser to authenticate with {provider.capitalize()}...[/dim]")
                webbrowser.open(res.url)
                
                auth_result = _wait_for_auth_code()
                if auth_result['code']:
                    supabase.auth.exchange_code_for_session({"auth_code": auth_result['code']})
                    console.print(f"[green]Successfully authenticated via {provider.capitalize()}![/green]")
                    break
                elif auth_result['access_token']:
                    supabase.auth.set_session(
                        access_token=auth_result['access_token'],
                        refresh_token=auth_result['refresh_token']
                    )
                    console.print(f"[green]Successfully authenticated via {provider.capitalize()}![/green]")
                    break
                else:
                    console.print("[red]Authentication failed: No code received.[/red]")
            except Exception as e:
                console.print(f"[red]OAuth failed: {str(e)}[/red]")
            continue
        
        email = Prompt.ask("Email")
        password = Prompt.ask("Password", password=True)
        
        try:
            if action == "s":
                res = supabase.auth.sign_up({"email": email, "password": password})
                console.print("[green]Sign up successful! You can now log in.[/green]")
                if res.user:
                    break
            elif action == "l":
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                console.print(f"[green]Logged in successfully as {res.user.email}[/green]")
                break
        except Exception as e:
            console.print(f"[red]Authentication failed: {str(e)}[/red]")
            
    # Save the user ID in global state and persist to file
    session = supabase.auth.get_session()
    if session and session.user:
        _save_session(session)
        # We store it globally so config.py can inject it into SQLAlchemy
        os.environ["CURRENT_USER_ID"] = session.user.id
