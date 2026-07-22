import sys
from whatsmynote.app.ui.app import WhatsMyNoteApp

import os
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
from dotenv import load_dotenv

def main():
    # Hardcoded public DSN for PyPI distribution
    sentry_dsn = "https://f7c616173ac3e671985d917b25f887e7@o4511774636310528.ingest.us.sentry.io/4511774741037056"
    
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.environ.get("ENV", "prod"), # Reads dev/stage locally, defaults to prod for PyPI users
        integrations=[sentry_logging],
        traces_sample_rate=0.1,
    )
    sentry_sdk.set_tag("component", "frontend")
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    app = WhatsMyNoteApp()
    app.run()

if __name__ == "__main__":
    main()
