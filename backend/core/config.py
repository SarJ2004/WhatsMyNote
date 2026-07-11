"""Configuration management for WhatsMyNote Backend."""

import os

def get_groq_api_key() -> str | None:
    """Get the GROQ API key from environment."""
    return os.environ.get("GROQ_API_KEY")

# --- App Constants (Replace these before publishing) ---
SUPABASE_URL = "INSERT_YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "INSERT_YOUR_SUPABASE_KEY_HERE"
DATABASE_URL = "INSERT_YOUR_DATABASE_URL_HERE"
# --------------------------------------------------------

def setup_backend_env() -> None:
    """Setup backend environment variables."""
    # Inject constants into environment so the rest of the app can use them
    os.environ["SUPABASE_URL"] = SUPABASE_URL
    os.environ["SUPABASE_KEY"] = SUPABASE_KEY
    os.environ["DATABASE_URL"] = DATABASE_URL
