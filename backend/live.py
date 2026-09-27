"""Staging entry. Render still starts backend.main, so staging is switched by env.

Set WMN_ENGINE=1 on the staging service only. Production does not set it.
"""

import os

if os.environ.get("WMN_ENGINE") == "1":
    from engine.api import create_live_app

    app = create_live_app()
else:
    from backend.main import app
