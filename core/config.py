"""Configuration management for WhatsMyNote."""

import os
from pathlib import Path

ENV_PATH = Path(".env")

def get_groq_api_key() -> str | None:
    """Get the GROQ API key from environment."""
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
    return os.environ.get("GROQ_API_KEY")

def set_groq_api_key(api_key: str) -> None:
    """Save the GROQ API key to .env file securely."""
    content = ""
    if ENV_PATH.exists():
        content = ENV_PATH.read_text()
    
    # Remove existing GROQ_API_KEY
    lines = [line for line in content.splitlines() if not line.startswith("GROQ_API_KEY=")]
    lines.append(f"GROQ_API_KEY={api_key}")
    
    ENV_PATH.write_text("\n".join(lines) + "\n")
    os.environ["GROQ_API_KEY"] = api_key
