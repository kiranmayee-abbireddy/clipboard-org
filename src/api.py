# src/api.py
import json
import os
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.clipboard_service import ClipboardService
from backend.database import ClipboardDatabase
from backend.categorizer import ContentCategorizer
from backend.crypto_handler import CryptoHandler

class ClipboardAPI:
    """JavaScript bridge between Python backend and PyWebView frontend"""

    def __init__(self, db_path: Optional[str] = None):
        self._database = ClipboardDatabase(db_path)
        self._categorizer = ContentCategorizer()
        self._crypto_handler: Optional[CryptoHandler] = None
        self._clipboard_service: Optional[ClipboardService] = None

        self.current_theme = "light"
        self.current_style = "sunrise"

        self.password_locked = True
        self.passkey_set = False

        self._load_settings()

    def _load_settings(self):
        """Load persistent user preferences and security state"""
        passkey_hash = self._database.get_setting('passkey_hash')
        self.passkey_set = passkey_hash is not None
        self.current_theme = self._database.get_setting('theme', 'light')
        self.current_style = self._database.get_setting('style', 'sunrise')

    def initialize_clipboard_service(self) -> bool:
        """Start the background clipboard polling engine"""
        if not self._clipboard_service:
            self._clipboard_service = ClipboardService(
                categorizer=self._categorizer,
                database=self._database,
                crypto_handler=self._crypto_handler
            )
            self._clipboard_service.start_monitoring()
        return True

    def shutdown(self):
        """Gracefully release resources on application exit"""
        if self._clipboard_service:
            self._clipboard_service.stop_monitoring()
        if self._database:
            self._database.close()

    # ============= Theme Settings =============

    def get_theme_settings(self) -> str:
        """Get current active theme mode and style name"""
        return json.dumps({
            'mode': self.current_theme,
            'style': self.current_style
        })

    def set_theme(self, mode: str, style: str) -> bool:
        """Update and persist theme settings"""
        self.current_theme = mode
        self.current_style = style
        self._database.set_setting('theme', mode)
        self._database.set_setting('style', style)
        return True

    # ============= Clip Operations =============

    def get_clips_version(self) -> int:
        """Returns monotonic version counter of the database for 0-latency polling"""
        return self._database.version

    def _process_clips_for_frontend(self, clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Optionally decrypt or annotate clips based on security state"""
        for clip in clips:
            if clip.get('category') == 'password':
                clip['is_locked'] = self.password_locked
                if not self.password_locked and self._crypto_handler and clip.get('encrypted_data'):
                    try:
                        clip['content'] = self._crypto_handler.decrypt(clip['encrypted_data'])
                    except Exception:
                        pass
        return clips

    def get_all_clips(self, limit: int = 100) -> str:
        """Retrieve all clips, with decryption applied if unlocked"""
        clips = self._database.get_all_clips(limit)
        return json.dumps(self._process_clips_for_frontend(clips))

    def get_clips_by_category(self, category: str, limit: int = 100) -> str:
        """Retrieve clips filtered by category"""
        clips = self._database.get_clips_by_category(category, limit)
        return json.dumps(self._process_clips_for_frontend(clips))

    def search_clips(self, query: str, limit: int = 50) -> str:
        """Search clips matching query string"""
        clips = self._database.search_clips(query, limit)
        return json.dumps(self._process_clips_for_frontend(clips))

    def get_clip_by_id(self, clip_id: int) -> str:
        """Get a single clip with decrypted content if unlocked"""
        clip = self._database.get_clip_by_id(clip_id)
        if not clip:
            return json.dumps(None)
        if clip.get('category') == 'password' and not self.password_locked and self._crypto_handler and clip.get('encrypted_data'):
            try:
                clip['content'] = self._crypto_handler.decrypt(clip['encrypted_data'])
            except Exception:
                pass
        return json.dumps(clip)

    def copy_clip(self, clip_id: int) -> bool:
        """Copy a specific clip content to system clipboard"""
        clip = self._database.get_clip_by_id(clip_id)
        if not clip:
            return False

        content = clip['content']
        # Decrypt password if encrypted
        if clip.get('is_encrypted') and clip.get('encrypted_data'):
            if not self._crypto_handler:
                return False
            try:
                content = self._crypto_handler.decrypt(clip['encrypted_data'])
            except Exception:
                return False

        if self._clipboard_service:
            return self._clipboard_service.copy_to_clipboard(content)
        else:
            # Fallback service instance if not yet started
            fallback = ClipboardService(self._categorizer, self._database)
            return fallback.copy_to_clipboard(content)

    def delete_clip(self, clip_id: int) -> bool:
        """Delete clip by ID"""
        return self._database.delete_clip(clip_id)

    def toggle_pin(self, clip_id: int) -> bool:
        """Toggle pin status of clip"""
        return self._database.toggle_pin(clip_id)

    def toggle_favorite(self, clip_id: int) -> bool:
        """Toggle favorite status of clip"""
        return self._database.toggle_favorite(clip_id)

    def manual_add_clip(self, content: str, category: str) -> bool:
        """Manually add or bump a snippet"""
        if not content or not content.strip():
            return False
        content = content.strip()

        encrypted_data = None
        content_to_store = content

        if category == 'password' and self._crypto_handler:
            try:
                encrypted_data = self._crypto_handler.encrypt(content)
                content_to_store = "[Encrypted Password]"
            except Exception:
                pass

        self._database.bump_or_add_clip(content_to_store, category, encrypted_data)
        return True

    def update_clip_content(self, clip_id: int, new_content: str) -> bool:
        """Update an existing clip's text content"""
        try:
            clip = self._database.get_clip_by_id(clip_id)
            if not clip:
                return False

            category = clip['category']
            encrypted_data = None
            content_to_store = new_content

            if category == 'password' and self._crypto_handler:
                try:
                    encrypted_data = self._crypto_handler.encrypt(new_content)
                    content_to_store = "[Encrypted Password]"
                except Exception:
                    pass

            return self._database.update_clip(clip_id, content_to_store, encrypted_data)
        except Exception as e:
            print(f"Error updating clip content: {e}")
            return False

    # ============= Password Security =============

    def setup_passkey(self, passkey: str) -> bool:
        """Set up a new passkey for password encryption"""
        if not passkey or len(passkey) < 4:
            return False
        if self.passkey_set:
            return False

        passkey_hash = hashlib.sha256(passkey.encode('utf-8')).hexdigest()
        self._database.set_setting('passkey_hash', passkey_hash)
        self._crypto_handler = CryptoHandler(passkey)

        if self._clipboard_service:
            self._clipboard_service.crypto_handler = self._crypto_handler

        self.passkey_set = True
        self.password_locked = False
        return True

    def verify_passkey(self, passkey: str) -> bool:
        """Verify passkey to unlock password clips"""
        passkey_hash = hashlib.sha256(passkey.encode('utf-8')).hexdigest()
        stored_hash = self._database.get_setting('passkey_hash')

        if passkey_hash == stored_hash:
            self._crypto_handler = CryptoHandler(passkey)
            if self._clipboard_service:
                self._clipboard_service.crypto_handler = self._crypto_handler
            self.password_locked = False
            return True
        return False

    def lock_passwords(self) -> bool:
        """Lock password clips and discard decryption cipher from memory"""
        self.password_locked = True
        self._crypto_handler = None
        if self._clipboard_service:
            self._clipboard_service.crypto_handler = None
        return True

    def is_password_locked(self) -> bool:
        return self.password_locked

    def is_passkey_set(self) -> bool:
        return self.passkey_set

    # ============= Category Settings =============

    def get_category_settings(self) -> str:
        """Get enabled/disabled categories for automatic capture"""
        if self._clipboard_service:
            return json.dumps(self._clipboard_service.enabled_categories)
        return json.dumps({
            'url': True, 'email': True, 'phone': True,
            'password': True, 'code': True, 'text': True
        })

    def set_category_enabled(self, category: str, enabled: bool) -> bool:
        """Update category enabled state"""
        if self._clipboard_service:
            self._clipboard_service.set_category_enabled(category, enabled)
            return True
        return False

    def get_category_info(self) -> str:
        """Return metadata (color and icon) for all categories"""
        categories = ['url', 'email', 'phone', 'password', 'code', 'text']
        info = {
            cat: {
                'color': self._categorizer.get_category_color(cat),
                'icon': self._categorizer.get_category_icon(cat)
            } for cat in categories
        }
        return json.dumps(info)

    # ============= Utilities & Data Management =============

    def cleanup_old_clips(self, days: int = 30) -> int:
        """Remove unpinned clips older than specified days"""
        return self._database.cleanup_old_clips(days)

    def export_clips(self) -> str:
        """Export all clips as a formatted JSON string"""
        clips = self._database.get_all_clips(limit=10000)
        return json.dumps(clips, indent=2)

    def export_clips_to_file(self) -> str:
        """Export clips to a file on Desktop or home directory and return file path"""
        clips = self._database.get_all_clips(limit=10000)
        data_str = json.dumps(clips, indent=2)

        # Prefer Desktop, fallback to Documents or Home
        home = Path.home()
        desktop = home / "Desktop"
        if desktop.exists() and desktop.is_dir():
            export_dir = desktop
        else:
            documents = home / "Documents"
            export_dir = documents if (documents.exists() and documents.is_dir()) else home

        export_path = export_dir / "clipbox_export.json"
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(data_str)

        return str(export_path)

    def import_clips(self, data: str) -> Dict[str, Any]:
        """Bulk import clips from JSON string"""
        try:
            clips = json.loads(data)
            if not isinstance(clips, list):
                return {'status': 'error', 'message': 'Invalid format: expected array'}
            count = self._database.import_clips_batch(clips)
            return {'status': 'success', 'count': count}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

    def get_app_stats(self) -> str:
        """Return detailed statistics about database and app performance"""
        return json.dumps(self._database.get_stats())
