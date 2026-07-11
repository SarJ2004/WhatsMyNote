"""Path management for WhatsMyNote CLI."""

from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "whatsmynote"
APP_AUTHOR = "whatsmynote"

def get_data_dir() -> Path:
    """Return the user data directory for the application."""
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_env_path() -> Path:
    """Return the path to the centralized .env file."""
    return get_data_dir() / "config.env"

def get_session_path() -> Path:
    """Return the path to the Supabase session file."""
    return get_data_dir() / "session.json"
