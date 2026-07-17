import sys
from whatsmynote.app.ui.app import WhatsMyNoteApp

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    app = WhatsMyNoteApp()
    app.run()

if __name__ == "__main__":
    main()
