# src/backend/database.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

class ClipboardDatabase:
    def __init__(self, db_path: str = "clipboard_data.db"):
        self.db_path = db_path
        self.connection = None
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        
        cursor = self.connection.cursor()
        
        # Main clips table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_pinned BOOLEAN DEFAULT 0,
                is_favorite BOOLEAN DEFAULT 0,
                encrypted_data BLOB,
                is_encrypted BOOLEAN DEFAULT 0
            )
        ''')
        
        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON clips(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON clips(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pinned ON clips(is_pinned)')
        
        self.connection.commit()
    
    def add_clip(self, content: str, category: str, encrypted_data: bytes = None) -> int:
        """Add new clip to database"""
        cursor = self.connection.cursor()
        is_encrypted = encrypted_data is not None
        
        cursor.execute('''
            INSERT INTO clips (content, category, encrypted_data, is_encrypted)
            VALUES (?, ?, ?, ?)
        ''', (content, category, encrypted_data, is_encrypted))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def get_all_clips(self, limit: int = 100) -> List[Dict]:
        """Retrieve all clips ordered by timestamp"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM clips 
            ORDER BY is_pinned DESC, timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_clips_by_category(self, category: str, limit: int = 100) -> List[Dict]:
        """Retrieve clips by category"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM clips 
            WHERE category = ?
            ORDER BY is_pinned DESC, timestamp DESC 
            LIMIT ?
        ''', (category, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def search_clips(self, query: str, limit: int = 50) -> List[Dict]:
        """Search clips by content"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM clips 
            WHERE content LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (f'%{query}%', limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def toggle_pin(self, clip_id: int) -> bool:
        """Toggle pin status of a clip"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT is_pinned FROM clips WHERE id = ?', (clip_id,))
        result = cursor.fetchone()
        
        if result:
            new_status = not result['is_pinned']
            cursor.execute('UPDATE clips SET is_pinned = ? WHERE id = ?', (new_status, clip_id))
            self.connection.commit()
            return new_status
        return False
    
    def toggle_favorite(self, clip_id: int) -> bool:
        """Toggle favorite status of a clip"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT is_favorite FROM clips WHERE id = ?', (clip_id,))
        result = cursor.fetchone()
        
        if result:
            new_status = not result['is_favorite']
            cursor.execute('UPDATE clips SET is_favorite = ? WHERE id = ?', (new_status, clip_id))
            self.connection.commit()
            return new_status
        return False
    
    def delete_clip(self, clip_id: int) -> bool:
        """Delete a clip by ID"""
        cursor = self.connection.cursor()
        cursor.execute('DELETE FROM clips WHERE id = ?', (clip_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def check_duplicate(self, content: str) -> bool:
        """Check if content already exists"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT id FROM clips WHERE content = ? LIMIT 1', (content,))
        return cursor.fetchone() is not None
    
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        cursor = self.connection.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result['value'] if result else default
    
    def set_setting(self, key: str, value: str):
        """Set a setting value"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
        ''', (key, value))
        self.connection.commit()
    
    def cleanup_old_clips(self, days: int = 30):
        """Delete clips older than specified days"""
        cursor = self.connection.cursor()
        cursor.execute('''
            DELETE FROM clips 
            WHERE datetime(timestamp) < datetime('now', '-' || ? || ' days')
            AND is_pinned = 0
        ''', (days,))
        self.connection.commit()
        return cursor.rowcount
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
