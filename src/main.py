# src/main.py
import webview
import sys
import threading
import time
from pathlib import Path
from api import ClipboardAPI
from background import create_startup_task

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
        import sys
        import os
        from pathlib import Path

        def get_base_path():
            if getattr(sys, 'frozen', False):
                # Running inside PyInstaller bundle
                return Path(sys._MEIPASS)
            else:
                # Running in normal Python environment
                return Path(__file__).parent

        base_path = get_base_path()

        # Construct path to frontend/index.html reliably
        frontend_path = base_path / 'frontend' / 'index.html'
        frontend_url = frontend_path.as_uri()
        
        # Create PyWebView window
        print("Exposed API methods:", dir(self.api))
        self.window = webview.create_window(
            'Clip Box',
            frontend_url,
            js_api=self.api,
            width=1000,
            height=700,
            resizable=True,
            min_size=(800, 600)
        )
        
        # Start clipboard service in background
        self.api.initialize_clipboard_service()
        
        # Start PyWebView (blocking call)
        webview.start(debug=True)  # Set debug=False to reduce console output

import os
import sys
import ctypes
import subprocess

def get_pythonw_executable():
    python_exe = sys.executable
    if python_exe.endswith("python.exe"):
        return python_exe.replace("python.exe", "pythonw.exe")
    else:
        # Fallback for non-standard naming
        return python_exe + "w"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def task_exists(task_name):
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", task_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True
    )
    return result.returncode == 0

def run_as_admin():
    script = sys.argv[0]
    params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1)
    sys.exit(0)

def ensure_scheduled_task(task_name):
    if not task_exists(task_name):
        if not is_admin():
            print("Elevating to admin to create background task...")
            run_as_admin()
        # Now create the task with your code (must be admin here)
        create_startup_task()
    else:
        print(f"Scheduled task '{task_name}' already exists, no need for admin.")
def main():
    """Application entry point"""
    ensure_scheduled_task("ClipboardMonitorBackground")
    app = ClipboardOrganizer()
    app.start()

if __name__ == '__main__':
    main()
