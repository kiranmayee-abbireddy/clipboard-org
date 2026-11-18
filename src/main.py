# src/main.py
import sys
import os
import argparse
from pathlib import Path
import webview

from api import ClipboardAPI

def get_base_path() -> Path:
    """Get root directory for application resources, handling PyInstaller packaging"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

class ClipboardOrganizer:
    """Main ClipBox desktop application controller"""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.api = ClipboardAPI()
        self.window = None

    def on_closed(self):
        """Cleanup handler when the window is closed"""
        if self.api:
            self.api.shutdown()

    def start(self):
        """Start the PyWebView desktop application"""
        base_path = get_base_path()
        frontend_path = base_path / 'frontend' / 'index.html'

        if not frontend_path.exists():
            # Fallback check for alternate dev locations
            alt_path = Path(__file__).resolve().parent.parent / 'src' / 'frontend' / 'index.html'
            if alt_path.exists():
                frontend_path = alt_path

        frontend_url = frontend_path.as_uri()

        # Initialize background clipboard capture engine
        self.api.initialize_clipboard_service()

        # Locate window icon if present
        icon_path = None
        for candidate in [base_path / 'clipbox.ico', Path(__file__).resolve().parent.parent / 'clipbox.ico']:
            if candidate.exists():
                icon_path = str(candidate)
                break

        # Create GUI window
        self.window = webview.create_window(
            title='ClipBox',
            url=frontend_url,
            js_api=self.api,
            width=1080,
            height=720,
            resizable=True,
            min_size=(750, 500),
            text_select=True,
            zoomable=True
        )

        # Wire closing event
        self.window.events.closed += self.on_closed

        # Start PyWebView loop (blocking)
        webview.start(debug=self.debug)

def main():
    """Application entry point with optional CLI flags"""
    parser = argparse.ArgumentParser(description="ClipBox - Aesthetic Clipboard Manager")
    parser.add_argument('--debug', action='store_true', help="Enable developer tools and webview debug logging")
    parser.add_argument('--headless', action='store_true', help="Run clipboard monitor in background without GUI")
    args = parser.parse_args()

    if args.headless:
        from clipboard_monitor import main as run_headless
        run_headless()
        return

    app = ClipboardOrganizer(debug=args.debug)
    app.start()

if __name__ == '__main__':
    main()
