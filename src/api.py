# src/api.py
import json
from typing import Optional
from backend.clipboard_service import ClipboardService
from backend.database import ClipboardDatabase
from backend.categorizer import ContentCategorizer
from backend.crypto_handler import CryptoHandler


class ClipboardAPI:
    """Bridge between PyQt backend and PyWebView frontend"""

    def __init__(self):
        self._database = ClipboardDatabase()
        self._categorizer = ContentCategorizer()
        self._crypto_handler = None
        self._clipboard_service = None
        
        self.current_theme = "light"
        self.current_style = "Sunrise"
        
        self.password_locked = True
        self.passkey_set = False
        
        self._load_settings()

    def _load_settings(self):
        passkey_hash = self._database.get_setting('passkey_hash')
        self.passkey_set = passkey_hash is not None
        self.current_theme = self._database.get_setting('theme', 'light')
        self.current_style = self._database.get_setting('style', 'Sunrise')

    def initialize_clipboard_service(self):
        if not self._clipboard_service:
            self._clipboard_service = ClipboardService(self._categorizer, self._database, self._crypto_handler)
            self._clipboard_service.load_settings()
            self._clipboard_service.start_monitoring()  # Called on main thread
        return True


    # ============= Clip Operations =============

    def get_all_clips(self, limit: int = 100) -> str:
        clips = self._database.get_all_clips(limit)
        return json.dumps(clips)

    def get_clips_by_category(self, category: str, limit: int = 100) -> str:
        clips = self._database.get_clips_by_category(category, limit)
        return json.dumps(clips)

    def search_clips(self, query: str) -> str:
        clips = self._database.search_clips(query)
        return json.dumps(clips)

    def copy_clip(self, clip_id: int) -> bool:
        clips = self._database.get_all_clips()
        clip = next((c for c in clips if c['id'] == clip_id), None)
        if not clip:
            return False

        content = clip['content']
        if clip['is_encrypted'] and clip.get('encrypted_data'):
            if not self.crypto_handler:
                return False
            try:
                content = self.crypto_handler.decrypt(clip['encrypted_data'])
            except:
                return False

        if self._clipboard_service:
            self._clipboard_service.copy_to_clipboard(content)
            return True
        return False

    def delete_clip(self, clip_id: int) -> bool:
        return self._database.delete_clip(clip_id)

    def toggle_pin(self, clip_id: int) -> bool:
        return self._database.toggle_pin(clip_id)

    def toggle_favorite(self, clip_id: int) -> bool:
        return self._database.toggle_favorite(clip_id)

    # ============= Password Security =============

    def setup_passkey(self, passkey: str) -> bool:
        if self.passkey_set:
            return False
        import hashlib
        passkey_hash = hashlib.sha256(passkey.encode()).hexdigest()
        self._database.set_setting('passkey_hash', passkey_hash)
        self.crypto_handler = CryptoHandler(passkey)
        if self._clipboard_service:
            self._clipboard_service.crypto_handler = self.crypto_handler
        self.passkey_set = True
        self.password_locked = False
        return True

    def verify_passkey(self, passkey: str) -> bool:
        import hashlib
        passkey_hash = hashlib.sha256(passkey.encode()).hexdigest()
        stored_hash = self._database.get_setting('passkey_hash')
        if passkey_hash == stored_hash:
            self._crypto_handler = CryptoHandler(passkey)
            if self._clipboard_service:
                self._clipboard_service.crypto_handler = self._crypto_handler
            self.password_locked = False
            return True
        return False

    def lock_passwords(self) -> bool:
        self.password_locked = True
        self._crypto_handler = None
        if self._clipboard_service:
            self._clipboard_service.crypto_handler = None
        return True

    def is_password_locked(self) -> bool:
        return self.password_locked

    def is_passkey_set(self) -> bool:
        return self.passkey_set

    # ============= Settings =============

    def get_category_settings(self) -> str:
        if self._clipboard_service:
            return json.dumps(self._clipboard_service.enabled_categories)
        return json.dumps({})

    def set_category_enabled(self, category: str, enabled: bool) -> bool:
        if self._clipboard_service:
            self._clipboard_service.set_category_enabled(category, enabled)
            return True
        return False

    def get_theme_settings(self) -> str:
        return json.dumps({
            'mode': self.current_theme,
            'style': self.current_style
        })

    def set_theme(self, mode: str, style: str) -> bool:
        self.current_theme = mode
        self.current_style = style
        self._database.set_setting('theme', mode)
        self._database.set_setting('style', style)
        return True

    # ============= Utilities =============

    def get_category_info(self) -> str:
        categories = ['url', 'email', 'phone', 'password', 'code', 'text']
        info = {
            cat: {
                'color': self._categorizer.get_category_color(cat),
                'icon': self._categorizer.get_category_icon(cat)
            } for cat in categories
        }
        return json.dumps(info)

    def cleanup_old_clips(self, days: int = 30) -> int:
        return self._database.cleanup_old_clips(days)

    def export_clips(self) -> str:
        clips = self._database.get_all_clips(limit=10000)
        return json.dumps(clips, indent=2)

    def manual_add_clip(self, content: str, category: str) -> bool:
        if not content.strip():
            return False
        if self._database.check_duplicate(content):
            return False
        encrypted_data = None
        if category == 'password' and self._crypto_handler:
            try:
                encrypted_data = self._crypto_handler.encrypt(content)
                content = "[Encrypted Password]"
            except:
                pass
        self._database.add_clip(content, category, encrypted_data)
        return True
