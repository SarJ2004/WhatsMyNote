"""Configuration management for WhatsMyNote Backend."""

import os

def get_groq_api_key() -> str | None:
    """Get the GROQ API key from environment."""
    return os.environ.get("GROQ_API_KEY")

# Supabase variables are expected to be set by Render or in a .env file
# --------------------------------------------------------

def setup_backend_env() -> None:
    """Setup backend environment variables."""
    from dotenv import load_dotenv
    load_dotenv()  # This ensures the backend reads your local .env file!
