"""CLI Configuration."""

import os
from dataclasses import dataclass
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

# Point the terminal at another engine, for example a local one while developing.
API_URL = os.environ.get("WMN_API_URL", API_URL).rstrip("/")

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

MODEL_KEY = "MODEL_KEY"
MODEL_BASE_URL = "MODEL_BASE_URL"
MODEL_NAME = "MODEL_NAME"
_LEGACY_KEY = "GROQ_API_KEY"
_MODEL_FIELDS = (MODEL_KEY, MODEL_BASE_URL, MODEL_NAME, _LEGACY_KEY)


@dataclass(frozen=True)
class ModelSettings:
    """The user's own model key, and optionally where and which model to call."""

    key: str = ""
    base_url: str = ""
    name: str = ""

    def headers(self) -> dict:
        """The per-request headers. Nothing is sent unless a key is saved."""
        if not self.key:
            return {}
        headers = {"X-Model-Key": self.key}
        if self.base_url:
            headers["X-Model-Base-URL"] = self.base_url
        if self.name:
            headers["X-Model-Name"] = self.name
        return headers

    def masked(self) -> str:
        """A hint that names the key without showing it."""
        if not self.key:
            return ""
        return "..." + self.key[-4:] if len(self.key) > 8 else "saved"


def check_model_settings(key: str, base_url: str, name: str) -> str | None:
    """Return a sentence describing what is wrong, or None when it can be saved."""
    if not key:
        return "Paste a model key."
    if any(ch.isspace() for ch in key):
        return "A model key has no spaces or line breaks. Paste it again."
    if base_url and not base_url.startswith(("https://", "http://")):
        return "The base URL starts with https://, for example https://api.openai.com/v1"
    if any(ch.isspace() for ch in base_url + name):
        return "The base URL and model name have no spaces."
    return None


class ModelKeyStore:
    """Keeps the model settings in a private file on this computer only."""

    def __init__(self, path: Path | None = None):
        self.path = path or get_env_path()

    def _read(self) -> list[str]:
        try:
            return self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []

    def load(self) -> ModelSettings:
        values = {}
        for line in self._read():
            name, sep, value = line.partition("=")
            if sep and name.strip() in _MODEL_FIELDS:
                values[name.strip()] = value.strip().strip('"').strip("'")
        return ModelSettings(
            key=values.get(MODEL_KEY) or values.get(_LEGACY_KEY) or "",
            base_url=values.get(MODEL_BASE_URL, ""),
            name=values.get(MODEL_NAME, ""),
        )

    def save(self, settings: ModelSettings) -> None:
        lines = self._others()
        lines.append(f"{MODEL_KEY}={settings.key}")
        if settings.base_url:
            lines.append(f"{MODEL_BASE_URL}={settings.base_url}")
        if settings.name:
            lines.append(f"{MODEL_NAME}={settings.name}")
        self._write(lines)

    def clear(self) -> None:
        self._write(self._others())

    def _others(self) -> list[str]:
        return [
            line for line in self._read()
            if line.partition("=")[0].strip() not in _MODEL_FIELDS
        ]

    def _write(self, lines: list[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(lines) + "\n" if lines else ""
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0)
        fd = os.open(self.path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        if os.name != "nt":
            os.chmod(self.path, 0o600)
