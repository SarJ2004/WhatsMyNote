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
        action = Prompt.ask("Do you want to (L)og in, (S)ign up, or (O)Auth [Google/GitHub]?", choices=["l", "s", "o", "q"], default="l").lower()
        if action == "q":
            exit(0)
            
        if action == "o":
            provider = Prompt.ask("Which provider?", choices=["google", "github"], default="google").lower()
            
            # Setup a one-time local server to receive the callback
            auth_code = [None]
            
            class OAuthCallbackHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    parsed_path = urlparse(self.path)
                    query_params = parse_qs(parsed_path.query)
                    
                    if 'code' in query_params:
                        auth_code[0] = query_params['code'][0]
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"<html><body><h1>Authentication Successful!</h1><p>You can close this tab and return to the terminal.</p></body></html>")
                    else:
                        self.send_response(400)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(b"<html><body><h1>Authentication Failed!</h1><p>Missing auth code.</p></body></html>")
                        
                def log_message(self, format, *args):
                    pass # Silence server logs

            server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
            
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
                
                # Wait for exactly one request
                server.handle_request()
                
                if auth_code[0]:
                    supabase.auth.exchange_code_for_session({"auth_code": auth_code[0]})
                    console.print(f"[green]Successfully authenticated via {provider.capitalize()}![/green]")
                    break
                else:
                    console.print("[red]Authentication failed: No code received.[/red]")
            except Exception as e:
                console.print(f"[red]OAuth failed: {str(e)}[/red]")
            finally:
                server.server_close()
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
