"""The process Render starts serves the engine and nothing else."""

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def test_the_backend_holds_only_the_live_entry_point():
    assert sorted(p.name for p in (ROOT / "backend").glob("*.py")) == ["__init__.py", "live.py"]
    source = (ROOT / "backend" / "live.py").read_text()
    imports = [line for line in source.splitlines() if line.startswith(("import ", "from "))]
    assert imports == ["from engine.api import create_live_app"]


def test_the_live_app_starts_from_the_environment_and_answers_health(dsn, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", dsn.replace("postgresql://", "postgresql+psycopg2://"))
    monkeypatch.setenv("SUPABASE_URL", "https://project.example")
    monkeypatch.setenv("SUPABASE_KEY", "anon")
    sys.modules.pop("backend.live", None)
    live = importlib.import_module("backend.live")
    with TestClient(live.app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.post("/chat", json={"message": "hi"}).json()["code"] == "unauthenticated"
