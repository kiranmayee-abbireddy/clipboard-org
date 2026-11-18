# src/clipboard_monitor.py
import signal
import sys
import os
import time
import logging

from backend.database import ClipboardDatabase
from backend.categorizer import ContentCategorizer
from backend.clipboard_service import ClipboardService

def main():
    """Headless CLI clipboard monitor runner"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    db = ClipboardDatabase()
    categorizer = ContentCategorizer()
    service = ClipboardService(categorizer, db, interval=0.5)

    def on_clip(content: str, category: str):
        preview = (content[:40] + '...') if len(content) > 40 else content
        logging.info(f"Captured [{category.upper()}]: {preview!r}")

    service.add_listener(on_clip)
    service.start_monitoring()
    logging.info("ClipBox background monitor started. Press Ctrl+C to exit.")

    def shutdown(sig, frame):
        logging.info("Shutting down monitor...")
        service.stop_monitoring()
        db.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
