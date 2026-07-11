"""CLI Configuration."""

import os
from pathlib import Path
from platformdirs import user_data_dir

# --- Replace these before publishing ---
API_URL = "http://localhost:8000"
SUPABASE_URL = "INSERT_YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "INSERT_YOUR_SUPABASE_KEY_HERE"
# ---------------------------------------

APP_NAME = "whatsmynote"
APP_AUTHOR = "whatsmynote"

def get_data_dir() -> Path:
    """Return the user data directory for the application."""
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_env_path() -> Path:
    return get_data_dir() / "config.env"

def get_session_path() -> Path:
    """Return the path to the Supabase session file."""
    return get_data_dir() / "session.json"

def get_groq_api_key() -> str | None:
    from dotenv import load_dotenv
    load_dotenv(get_env_path())
    return os.environ.get("GROQ_API_KEY")

def ensure_env_config() -> None:
    from dotenv import load_dotenv
    from rich.console import Console
    from rich.prompt import Prompt
    
    env_path = get_env_path()
    console = Console()
    
    if not env_path.exists():
        env_path.touch(mode=0o600, exist_ok=True)
        
    load_dotenv(env_path)
    
    if not os.environ.get("GROQ_API_KEY"):
        console.print("[bold yellow]First time setup: Missing required configuration[/bold yellow]")
        val = Prompt.ask("Enter GROQ_API_KEY", password=True)
        if not val:
            console.print("[red]GROQ_API_KEY is required. Exiting.[/red]")
            exit(1)
            
        content = env_path.read_text()
        lines = [line for line in content.splitlines() if not line.startswith("GROQ_API_KEY=")]
        lines.append(f"GROQ_API_KEY={val}")
        env_path.write_text("\n".join(lines) + "\n")
        os.environ["GROQ_API_KEY"] = val
        console.print("[green]Configuration saved successfully.[/green]")
