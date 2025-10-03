# src/backend/clipboard_service.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QClipboard
from typing import Callable, Optional
import threading
import time

class ClipboardService(QObject):
    """PyQt-based clipboard monitoring service"""
    
    # Signals for clipboard events
    clip_changed = pyqtSignal(str, str)  # content, category
    
    def __init__(self, categorizer, database, crypto_handler=None):
        super().__init__()
        
        # Initialize QApplication if not exists
        self.app = QApplication.instance()
        if not self.app:
            self.app = QApplication(sys.argv)
        
        self.clipboard = self.app.clipboard()
        self.categorizer = categorizer
        self.database = database
        self.crypto_handler = crypto_handler
        
        self.last_content = ""
        self.is_monitoring = False
        
        # Storage settings (which categories to save)
        self.enabled_categories = {
            'url': True,
            'email': True,
            'phone': True,
            'password': True,
            'code': True,
            'text': True
        }
        
        # Connect clipboard signal
        self.clipboard.dataChanged.connect(self._on_clipboard_change)
    
    def _on_clipboard_change(self):
        """Handle clipboard content change"""
        if not self.is_monitoring:
            return
        
        content = self.clipboard.text().strip()
        
        # Ignore empty or duplicate content
        if not content or content == self.last_content:
            return
        
        self.last_content = content
        
        # Categorize content
        category = self.categorizer.categorize(content)
        
        # Check if this category should be stored
        if not self.enabled_categories.get(category, True):
            return
        
        # Check for duplicates
        if self.database.check_duplicate(content):
            return
        
        # Handle password encryption
        encrypted_data = None
        if category == 'password' and self.crypto_handler:
            try:
                encrypted_data = self.crypto_handler.encrypt(content)
                content = "[Encrypted Password]"  # Mask content
            except:
                pass  # If encryption fails, store as plain text
        
        # Store in database
        self.database.add_clip(content, category, encrypted_data)
        self.clip_changed.emit(content, category)
    
    def start_monitoring(self):
        """Start clipboard monitoring"""
        self.is_monitoring = True
        print("Clipboard monitoring started")
    
    def stop_monitoring(self):
        """Stop clipboard monitoring"""
        self.is_monitoring = False
        print("Clipboard monitoring stopped")
    
    def copy_to_clipboard(self, content: str):
        """Copy content to system clipboard"""
        self.clipboard.setText(content)
    
    def set_category_enabled(self, category: str, enabled: bool):
        """Enable/disable storage for specific category"""
        self.enabled_categories[category] = enabled
        # Persist to database
        import json
        self.database.set_setting('enabled_categories', json.dumps(self.enabled_categories))
    
    def load_settings(self):
        """Load settings from database"""
        import json
        settings_json = self.database.get_setting('enabled_categories')
        if settings_json:
            self.enabled_categories = json.loads(settings_json)
