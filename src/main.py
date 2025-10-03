# src/main.py
import webview
import sys
import threading
import time
from pathlib import Path
from api import ClipboardAPI

# Import QApplication at module level
from PyQt6.QtWidgets import QApplication

class ClipboardOrganizer:
    """Main application class"""
    
    def __init__(self):
        # Initialize QApplication in main thread BEFORE anything else
        self.qt_app = QApplication.instance()
        if not self.qt_app:
            self.qt_app = QApplication(sys.argv)
        
        self.api = ClipboardAPI()
        self.window = None
    
    def start(self):
        """Start the application"""
        # Get frontend path
        frontend_path = Path(__file__).parent / 'frontend' / 'index.html'
        
        # Create PyWebView window
        self.window = webview.create_window(
            'Clipboard Organizer',
            frontend_path.as_uri(),
            js_api=self.api,
            width=1000,
            height=700,
            resizable=True,
            min_size=(800, 600)
        )
        
        # Start clipboard service in background
        def initialize_backend():
            # Give PyWebView time to initialize
            time.sleep(1)
            self.api.initialize_clipboard_service()
        
        threading.Thread(target=initialize_backend, daemon=True).start()
        
        # Start PyWebView (blocking call)
        webview.start(debug=False)  # Set debug=False to reduce console output

def main():
    """Application entry point"""
    app = ClipboardOrganizer()
    app.start()

if __name__ == '__main__':
    main()
