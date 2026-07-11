"""Configuration management for WhatsMyNote Backend."""

import os

def get_groq_api_key() -> str | None:
    """Get the GROQ API key from environment."""
    return os.environ.get("GROQ_API_KEY")

# --- App Constants (Optional: Set these directly or use Render Env Vars) ---
SUPABASE_URL_CONSTANT = "INSERT_YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY_CONSTANT = "INSERT_YOUR_SUPABASE_KEY_HERE"
DATABASE_URL_CONSTANT = "INSERT_YOUR_DATABASE_URL_HERE"
# --------------------------------------------------------

def setup_backend_env() -> None:
    """Setup backend environment variables."""
    if SUPABASE_URL_CONSTANT and "INSERT_YOUR" not in SUPABASE_URL_CONSTANT:
        os.environ.setdefault("SUPABASE_URL", SUPABASE_URL_CONSTANT)
    if SUPABASE_KEY_CONSTANT and "INSERT_YOUR" not in SUPABASE_KEY_CONSTANT:
        os.environ.setdefault("SUPABASE_KEY", SUPABASE_KEY_CONSTANT)
    if DATABASE_URL_CONSTANT and "INSERT_YOUR" not in DATABASE_URL_CONSTANT:
        os.environ.setdefault("DATABASE_URL", DATABASE_URL_CONSTANT)
