import signal
import sys
import os
from backend.database import ClipboardDatabase
from backend.categorizer import ContentCategorizer
from backend.clipboard_service import ClipboardPoller
import time


def main():
    db = ClipboardDatabase()
    categorizer = ContentCategorizer()
    poller = ClipboardPoller(categorizer, interval=1.0)

    poller.start()
    print("Clipboard monitor running in background (non-Qt)...")

    def signal_handler(sig, frame):
        print("Shutting down clipboard monitor...")
        poller.stop()
        db.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            print("Clipboard monitor running in background (non-Qt)...")
            time.sleep(1)  # wait indefinitely
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
