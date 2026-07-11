"""WhatsMyNote CLI — single entry point."""
import sys
import os

if sys.platform == "win32":
    # Force UTF-8 encoding for rich/plotext on Windows legacy terminals
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from app.chat import main

if __name__ == "__main__":
    main()
