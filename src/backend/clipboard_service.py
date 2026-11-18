# src/backend/clipboard_service.py
import sys
import time
import threading
import logging
from typing import Optional, Callable, Dict, List, Any

# Cross-platform clipboard backend
_WIN32_AVAILABLE = False
try:
    import win32clipboard
    import win32con
    _WIN32_AVAILABLE = True
except ImportError:
    pass

class ClipboardService:
    """
    High-performance clipboard monitoring service with robust Windows win32clipboard
    handling, automatic retry on locked clipboards, and category-aware filtering.
    """

    def __init__(self, categorizer, database, crypto_handler: Optional[object] = None, interval: float = 0.5):
        self.categorizer = categorizer
        self.database = database
        self.crypto_handler = crypto_handler
        self.interval = interval

        self.last_clip = ""
        self.monitoring = False
        self._stop_event = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        self._listeners: List[Callable[[str, str], None]] = []

        # Enabled categories for automatic capture
        self.enabled_categories: Dict[str, bool] = {
            'url': True,
            'email': True,
            'phone': True,
            'password': True,
            'code': True,
            'text': True
        }

        self.load_settings()

    def add_listener(self, callback: Callable[[str, str], None]):
        """Register a callback for clip change notifications: callback(content, category)"""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[str, str], None]):
        """Unregister a clip change listener"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, content: str, category: str):
        for listener in self._listeners:
            try:
                listener(content, category)
            except Exception as e:
                logging.debug(f"Listener notification error: {e}")

    # ============= Low-level Clipboard I/O =============

    def get_system_clipboard_text(self) -> str:
        """Read unicode text from system clipboard with retries"""
        if _WIN32_AVAILABLE:
            for _ in range(3):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                            data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                            return data if data else ""
                    finally:
                        win32clipboard.CloseClipboard()
                    return ""
                except Exception:
                    time.sleep(0.05)
            return ""
        else:
            # Fallback for non-windows or missing pywin32
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                text = root.clipboard_get()
                root.destroy()
                return text if text else ""
            except Exception:
                return ""

    def copy_to_clipboard(self, content: str) -> bool:
        """Write unicode text to system clipboard"""
        if not content:
            return False

        # Set last_clip immediately to prevent capturing our own copy action
        self.last_clip = content.strip()

        if _WIN32_AVAILABLE:
            for _ in range(3):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, content)
                        return True
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception:
                    time.sleep(0.05)
            return False
        else:
            try:
                import tkinter as tk
                root = tk.Tk()
                root.withdraw()
                root.clipboard_clear()
                root.clipboard_append(content)
                root.update()
                root.destroy()
                return True
            except Exception as e:
                logging.error(f"Failed to copy to clipboard: {e}")
                return False

    # ============= Polling & Processing =============

    def check_clipboard(self):
        """Poll clipboard content, categorize, encrypt if needed, and store"""
        clip = self.get_system_clipboard_text()
        clip = clip.strip() if clip else ""

        if not clip or clip == self.last_clip or not self.monitoring:
            return

        self.last_clip = clip

        category = self.categorizer.categorize(clip)

        if not self.enabled_categories.get(category, True):
            return

        encrypted_data = None
        clip_to_store = clip

        if category == 'password' and self.crypto_handler:
            try:
                encrypted_data = self.crypto_handler.encrypt(clip)
                clip_to_store = "[Encrypted Password]"
            except Exception as e:
                logging.debug(f"Encryption failed, storing plain: {e}")

        # Add or bump existing clip to the top
        clip_id, is_new = self.database.bump_or_add_clip(clip_to_store, category, encrypted_data)

        self._notify_listeners(clip_to_store, category)

    def _poll_loop(self):
        """Background thread loop"""
        while not self._stop_event.is_set():
            try:
                self.check_clipboard()
            except Exception as e:
                logging.debug(f"Error in clipboard polling loop: {e}")
            self._stop_event.wait(self.interval)

    def start_monitoring(self):
        """Start periodic clipboard polling thread"""
        if self.monitoring:
            return
        self.monitoring = True
        self._stop_event.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True, name="ClipBox-Monitor")
        self._poll_thread.start()

    def stop_monitoring(self):
        """Stop periodic clipboard polling thread"""
        self.monitoring = False
        self._stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=1.0)
            self._poll_thread = None

    # ============= Settings =============

    def set_category_enabled(self, category: str, enabled: bool):
        """Enable or disable automatic capture for a category"""
        self.enabled_categories[category] = enabled
        import json
        self.database.set_setting('enabled_categories', json.dumps(self.enabled_categories))

    def load_settings(self):
        """Load enabled categories from database"""
        import json
        settings_json = self.database.get_setting('enabled_categories')
        if settings_json:
            try:
                saved = json.loads(settings_json)
                self.enabled_categories.update(saved)
            except Exception:
                pass

# Backward compatibility alias
ClipboardPoller = ClipboardService
