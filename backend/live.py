"""The process Render starts: `uvicorn backend.live:app`. It serves the engine
and nothing else; the old backend is gone."""

from engine.api import create_live_app

app = create_live_app()
