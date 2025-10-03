# src/backend/clipboard_service.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Optional
import win32clipboard
import threading
import time


class ClipboardService(QObject):
    """PyQt-based clipboard monitoring service with polling using win32clipboard"""

    clip_changed = pyqtSignal(str, str)  # content, category

    def __init__(self, categorizer, database, crypto_handler: Optional[object] = None):
        super().__init__()

        # Ensure a QApplication instance exists
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)

        self.categorizer = categorizer
        self.database = database
        self.crypto_handler = crypto_handler

        self.last_clip = ""

        # Enabled categories: which types to save automatically
        self.enabled_categories = {
            'url': True,
            'email': True,
            'phone': True,
            'password': True,
            'code': True,
            'text': True
        }

        self.monitoring = False
        self._poll_thread = None


    def check_clipboard(self):
        """Poll clipboard text content and process new entries"""
        
        try:
            win32clipboard.OpenClipboard()
            clip = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        except TypeError:
            clip = ''
        except Exception as e:
            print(f"Clipboard access error: {e}")
            clip = ''
        finally:
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

        clip = clip.strip() if clip else ""
        if not clip or clip == self.last_clip or not self.monitoring:
            return

        self.last_clip = clip

        category = self.categorizer.categorize(clip)

        if not self.enabled_categories.get(category, True):
            return

        if self.database.check_duplicate(clip):
            return

        encrypted_data = None
        clip_to_store = clip
        if category == 'password' and self.crypto_handler:
            try:
                encrypted_data = self.crypto_handler.encrypt(clip)
                clip_to_store = "[Encrypted Password]"
            except Exception:
                clip_to_store = clip

        self.database.add_clip(clip_to_store, category, encrypted_data)

        self.clip_changed.emit(clip_to_store, category)
    
    def _poll_loop(self):
        while self.monitoring:
            self.check_clipboard()
            time.sleep(1)

    def start_monitoring(self):
        """Start periodic clipboard polling"""
        if self.monitoring:
            return
        self.monitoring = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop_monitoring(self):
        self.monitoring = False
        if self._poll_thread:
            self._poll_thread.join()

    def copy_to_clipboard(self, content: str):
        """Copy text content back to system clipboard"""
        self.app.clipboard().setText(content)

    def set_category_enabled(self, category: str, enabled: bool):
        """Enable or disable storage for a clipboard content category"""
        self.enabled_categories[category] = enabled
        import json
        self.database.set_setting('enabled_categories', json.dumps(self.enabled_categories))

    def load_settings(self):
        """Load enabled category settings from the database"""
        import json
        settings_json = self.database.get_setting('enabled_categories')
        if settings_json:
            try:
                self.enabled_categories = json.loads(settings_json)
            except json.JSONDecodeError:
                pass  # ignore invalid JSON, keep default settings

