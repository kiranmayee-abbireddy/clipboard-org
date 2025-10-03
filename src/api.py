# src/api.py
import json
from typing import Dict, List, Optional
from backend.clipboard_service import ClipboardService
from backend.database import ClipboardDatabase
from backend.categorizer import ContentCategorizer
from backend.crypto_handler import CryptoHandler

class ClipboardAPI:
    """Bridge between PyQt backend and PyWebView frontend"""
    
    def __init__(self):
        self.database = ClipboardDatabase()
        self.categorizer = ContentCategorizer()
        self.crypto_handler = None
        self.clipboard_service = None
        
        # Track password lock state
        self.password_locked = True
        self.passkey_set = False
        
        # Load settings
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from database"""
        # Check if passkey is set
        passkey_hash = self.database.get_setting('passkey_hash')
        self.passkey_set = passkey_hash is not None
        
        # Load theme settings
        self.current_theme = self.database.get_setting('theme', 'light')
        self.current_style = self.database.get_setting('style', 'Sunrise')
    
    def initialize_clipboard_service(self):
        """Initialize clipboard monitoring service"""
        self.clipboard_service = ClipboardService(
            self.categorizer,
            self.database,
            self.crypto_handler
        )
        self.clipboard_service.load_settings()
        self.clipboard_service.start_monitoring()
        
        # Connect signal to update UI
        self.clipboard_service.clip_changed.connect(self._on_new_clip)
        
        return True
    
    def _on_new_clip(self, content: str, category: str):
        """Handle new clip detected - notify frontend"""
        # This will be called from PyQt thread
        # Frontend will poll for new clips or we can use JS callbacks
        pass
    
    # ============= Clip Operations =============
    
    def get_all_clips(self, limit: int = 100) -> str:
        """Get all clips as JSON"""
        clips = self.database.get_all_clips(limit)
        return json.dumps(clips)
    
    def get_clips_by_category(self, category: str, limit: int = 100) -> str:
        """Get clips by category as JSON"""
        clips = self.database.get_clips_by_category(category, limit)
        return json.dumps(clips)
    
    def search_clips(self, query: str) -> str:
        """Search clips by content"""
        clips = self.database.search_clips(query)
        return json.dumps(clips)
    
    def copy_clip(self, clip_id: int) -> bool:
        """Copy clip content to clipboard"""
        clips = self.database.get_all_clips()
        clip = next((c for c in clips if c['id'] == clip_id), None)
        
        if not clip:
            return False
        
        content = clip['content']
        
        # If encrypted, decrypt first
        if clip['is_encrypted'] and clip['encrypted_data']:
            if not self.crypto_handler:
                return False
            try:
                content = self.crypto_handler.decrypt(clip['encrypted_data'])
            except:
                return False
        
        self.clipboard_service.copy_to_clipboard(content)
        return True
    
    def delete_clip(self, clip_id: int) -> bool:
        """Delete a clip"""
        return self.database.delete_clip(clip_id)
    
    def toggle_pin(self, clip_id: int) -> bool:
        """Toggle pin status"""
        return self.database.toggle_pin(clip_id)
    
    def toggle_favorite(self, clip_id: int) -> bool:
        """Toggle favorite status"""
        return self.database.toggle_favorite(clip_id)
    
    # ============= Password Security =============
    
    def setup_passkey(self, passkey: str) -> bool:
        """Setup initial passkey"""
        if self.passkey_set:
            return False
        
        # Hash and store passkey
        import hashlib
        passkey_hash = hashlib.sha256(passkey.encode()).hexdigest()
        self.database.set_setting('passkey_hash', passkey_hash)
        
        # Initialize crypto handler
        self.crypto_handler = CryptoHandler(passkey)
        self.clipboard_service.crypto_handler = self.crypto_handler
        
        self.passkey_set = True
        self.password_locked = False
        
        return True
    
    def verify_passkey(self, passkey: str) -> bool:
        """Verify passkey and unlock"""
        import hashlib
        passkey_hash = hashlib.sha256(passkey.encode()).hexdigest()
        stored_hash = self.database.get_setting('passkey_hash')
        
        if passkey_hash == stored_hash:
            self.crypto_handler = CryptoHandler(passkey)
            self.clipboard_service.crypto_handler = self.crypto_handler
            self.password_locked = False
            return True
        
        return False
    
    def lock_passwords(self) -> bool:
        """Lock password access"""
        self.password_locked = True
        self.crypto_handler = None
        return True
    
    def is_password_locked(self) -> bool:
        """Check if passwords are locked"""
        return self.password_locked
    
    def is_passkey_set(self) -> bool:
        """Check if passkey is configured"""
        return self.passkey_set
    
    # ============= Settings =============
    
    def get_category_settings(self) -> str:
        """Get which categories are enabled for storage"""
        if self.clipboard_service:
            return json.dumps(self.clipboard_service.enabled_categories)
        return json.dumps({})
    
    def set_category_enabled(self, category: str, enabled: bool) -> bool:
        """Enable/disable storage for category"""
        if self.clipboard_service:
            self.clipboard_service.set_category_enabled(category, enabled)
            return True
        return False
    
    def get_theme_settings(self) -> str:
        """Get current theme settings"""
        return json.dumps({
            'mode': self.current_theme,
            'style': self.current_style
        })
    
    def set_theme(self, mode: str, style: str) -> bool:
        """Set theme mode and style"""
        self.current_theme = mode
        self.current_style = style
        self.database.set_setting('theme', mode)
        self.database.set_setting('style', style)
        return True
    
    # ============= Utilities =============
    
    def get_category_info(self) -> str:
        """Get category colors and icons"""
        categories = ['url', 'email', 'phone', 'password', 'code', 'text']
        info = {}
        for cat in categories:
            info[cat] = {
                'color': self.categorizer.get_category_color(cat),
                'icon': self.categorizer.get_category_icon(cat)
            }
        return json.dumps(info)
    
    def cleanup_old_clips(self, days: int = 30) -> int:
        """Cleanup clips older than specified days"""
        return self.database.cleanup_old_clips(days)
    
    def export_clips(self) -> str:
        """Export all clips as JSON"""
        clips = self.database.get_all_clips(limit=10000)
        return json.dumps(clips, indent=2)
