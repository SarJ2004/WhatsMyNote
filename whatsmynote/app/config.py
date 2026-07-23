"""CLI Configuration."""

import os
from pathlib import Path
from platformdirs import user_data_dir

from dotenv import load_dotenv
load_dotenv()

# --- Replace these before publishing ---
env_mode = os.environ.get("ENV")
if env_mode == "dev":
    API_URL = "http://127.0.0.1:8000"
    SUPABASE_URL = "https://wxnihqslmljbidbortzp.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind4bmlocXNsbWxqYmlkYm9ydHpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNjk1ODksImV4cCI6MjA5OTg0NTU4OX0.qpJV9rQhWZ38hLlwihEewwDEtwVSX-H_e-VCkR1EiyU"
elif env_mode == "stage":
    API_URL = "https://whatsmynote-staging.onrender.com"
    SUPABASE_URL = "https://wxnihqslmljbidbortzp.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind4bmlocXNsbWxqYmlkYm9ydHpwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQyNjk1ODksImV4cCI6MjA5OTg0NTU4OX0.qpJV9rQhWZ38hLlwihEewwDEtwVSX-H_e-VCkR1EiyU"
elif env_mode == "prod":
    API_URL = "https://whatsmynote.onrender.com"
    SUPABASE_URL = "https://emcdruetkqkrplrrxqbm.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVtY2RydWV0a3FrcnBscnJ4cWJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM3NjQ1NTksImV4cCI6MjA5OTM0MDU1OX0.-GRm3ZhaFGDGyy8ocDq0tAov0CxCOwCK9K9JeWPTCvY"
else:
    # Default to production if ENV is not set or unrecognized
    API_URL = "https://whatsmynote.onrender.com"
    SUPABASE_URL = "https://emcdruetkqkrplrrxqbm.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVtY2RydWV0a3FrcnBscnJ4cWJtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODM3NjQ1NTksImV4cCI6MjA5OTM0MDU1OX0.-GRm3ZhaFGDGyy8ocDq0tAov0CxCOwCK9K9JeWPTCvY"
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

def set_groq_api_key(api_key: str) -> None:
    env_path = get_env_path()
    content = ""
    if env_path.exists():
        content = env_path.read_text()
    
    lines = [line for line in content.splitlines() if not line.startswith("GROQ_API_KEY=")]
    lines.append(f"GROQ_API_KEY={api_key}")
    env_path.write_text("\n".join(lines) + "\n")
    os.environ["GROQ_API_KEY"] = api_key
