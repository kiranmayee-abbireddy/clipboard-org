# src/backend/database.py
import sqlite3
import json
import base64
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

def get_app_data_path() -> str:
    """Get the standard database path in local user app data folder"""
    base_dir = os.getenv('LOCALAPPDATA')
    if not base_dir:
        base_dir = str(Path.home() / ".local" / "share")
    app_dir = os.path.join(base_dir, "ClipboardOrganizer")
    os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "clipboard_data.db")

class ClipboardDatabase:
    """High-performance SQLite database layer for ClipBox with WAL mode and indexing"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path if db_path else get_app_data_path()
        self.connection = None
        self._lock = threading.RLock()
        self._version = 1
        self.init_database()

    def _get_connection(self) -> sqlite3.Connection:
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            self.connection.row_factory = sqlite3.Row
            # Enable SQLite performance and safety optimizations
            self.connection.execute('PRAGMA journal_mode = WAL;')
            self.connection.execute('PRAGMA synchronous = NORMAL;')
            self.connection.execute('PRAGMA busy_timeout = 5000;')
            self.connection.execute('PRAGMA temp_store = MEMORY;')
        return self.connection

    def init_database(self):
        """Initialize database with tables and performance indexes"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

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

            # Performance Indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_clips_order ON clips(is_pinned DESC, timestamp DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_category_order ON clips(category, is_pinned DESC, timestamp DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_content ON clips(content)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON clips(timestamp)')

            conn.commit()

    @property
    def version(self) -> int:
        return self._version

    def _bump_version(self):
        self._version += 1

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite Row to dictionary with JSON-safe data types"""
        item = dict(row)
        # Handle BLOB data gracefully for JSON serialization
        if 'encrypted_data' in item:
            data = item['encrypted_data']
            if isinstance(data, bytes):
                item['encrypted_data'] = base64.b64encode(data).decode('ascii')
            elif data is None:
                item['encrypted_data'] = None
        return item

    def add_clip(self, content: str, category: str, encrypted_data: Optional[bytes] = None) -> int:
        """Add new clip to database"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            is_encrypted = 1 if encrypted_data is not None else 0

            cursor.execute('''
                INSERT INTO clips (content, category, encrypted_data, is_encrypted, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (content, category, encrypted_data, is_encrypted))

            clip_id = cursor.lastrowid
            conn.commit()
            self._bump_version()
            return clip_id

    def bump_or_add_clip(self, content: str, category: str, encrypted_data: Optional[bytes] = None) -> Tuple[int, bool]:
        """
        If content exists in database, bump its timestamp to NOW and return (id, False).
        Otherwise insert new clip and return (id, True).
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, is_pinned FROM clips WHERE content = ? LIMIT 1', (content,))
            row = cursor.fetchone()

            if row:
                clip_id = row['id']
                cursor.execute('UPDATE clips SET timestamp = CURRENT_TIMESTAMP WHERE id = ?', (clip_id,))
                conn.commit()
                self._bump_version()
                return (clip_id, False)
            else:
                is_encrypted = 1 if encrypted_data is not None else 0
                cursor.execute('''
                    INSERT INTO clips (content, category, encrypted_data, is_encrypted, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (content, category, encrypted_data, is_encrypted))
                clip_id = cursor.lastrowid
                conn.commit()
                self._bump_version()
                return (clip_id, True)

    def get_all_clips(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve all clips ordered by pinned status and timestamp"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, category, timestamp, is_pinned, is_favorite, encrypted_data, is_encrypted
                FROM clips 
                ORDER BY is_pinned DESC, timestamp DESC 
                LIMIT ?
            ''', (limit,))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_clips_by_category(self, category: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve clips filtered by category"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, category, timestamp, is_pinned, is_favorite, encrypted_data, is_encrypted
                FROM clips 
                WHERE category = ?
                ORDER BY is_pinned DESC, timestamp DESC 
                LIMIT ?
            ''', (category, limit))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def search_clips(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search clips by content (case-insensitive substring)"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, category, timestamp, is_pinned, is_favorite, encrypted_data, is_encrypted
                FROM clips 
                WHERE content LIKE ? 
                ORDER BY is_pinned DESC, timestamp DESC 
                LIMIT ?
            ''', (f'%{query}%', limit))
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_clip_by_id(self, clip_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a single clip by ID"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, content, category, timestamp, is_pinned, is_favorite, encrypted_data, is_encrypted
                FROM clips WHERE id = ?
            ''', (clip_id,))
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def update_clip(self, clip_id: int, content: str, encrypted_data: Optional[bytes] = None) -> bool:
        """Update content and optional encryption of an existing clip"""
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                is_encrypted = 1 if encrypted_data is not None else 0
                cursor.execute(
                    "UPDATE clips SET content = ?, encrypted_data = ?, is_encrypted = ? WHERE id = ?",
                    (content, encrypted_data, is_encrypted, clip_id)
                )
                conn.commit()
                self._bump_version()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Database error updating clip: {e}")
                return False

    def toggle_pin(self, clip_id: int) -> bool:
        """Toggle pin status of a clip"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_pinned FROM clips WHERE id = ?', (clip_id,))
            row = cursor.fetchone()
            if row:
                new_status = 1 if not row['is_pinned'] else 0
                cursor.execute('UPDATE clips SET is_pinned = ? WHERE id = ?', (new_status, clip_id))
                conn.commit()
                self._bump_version()
                return bool(new_status)
            return False

    def toggle_favorite(self, clip_id: int) -> bool:
        """Toggle favorite status of a clip"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT is_favorite FROM clips WHERE id = ?', (clip_id,))
            row = cursor.fetchone()
            if row:
                new_status = 1 if not row['is_favorite'] else 0
                cursor.execute('UPDATE clips SET is_favorite = ? WHERE id = ?', (new_status, clip_id))
                conn.commit()
                self._bump_version()
                return bool(new_status)
            return False

    def delete_clip(self, clip_id: int) -> bool:
        """Delete a clip by ID"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM clips WHERE id = ?', (clip_id,))
            conn.commit()
            if cursor.rowcount > 0:
                self._bump_version()
                return True
            return False

    def check_duplicate(self, content: str) -> bool:
        """Check if content exists anywhere in database"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM clips WHERE content = ? LIMIT 1', (content,))
            return cursor.fetchone() is not None

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            result = cursor.fetchone()
            return result['value'] if result else default

    def set_setting(self, key: str, value: str):
        """Set a setting value"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value)
                VALUES (?, ?)
            ''', (key, value))
            conn.commit()

    def cleanup_old_clips(self, days: int = 30) -> int:
        """Delete unpinned clips older than specified days"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            offset = f"-{int(days)} days"
            cursor.execute('''
                DELETE FROM clips 
                WHERE datetime(timestamp) < datetime('now', ?)
                AND is_pinned = 0
            ''', (offset,))
            conn.commit()
            count = cursor.rowcount
            if count > 0:
                self._bump_version()
            return count

    def write_clip(self, clip: Dict[str, Any]) -> int:
        """Insert a single clip dictionary"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            encrypted_data = clip.get('encrypted_data')
            if isinstance(encrypted_data, str) and encrypted_data:
                try:
                    encrypted_data = base64.b64decode(encrypted_data.encode('ascii'))
                except Exception:
                    pass

            cursor.execute('''
                INSERT INTO clips 
                (content, category, timestamp, is_pinned, is_favorite, encrypted_data, is_encrypted)
                VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, ?, ?, ?)
            ''', (
                clip.get('content', ''),
                clip.get('category', 'text'),
                clip.get('timestamp'),
                clip.get('is_pinned', 0),
                clip.get('is_favorite', 0),
                encrypted_data,
                clip.get('is_encrypted', 0)
            ))
            conn.commit()
            self._bump_version()
            return cursor.lastrowid

    def import_clips_batch(self, clips: List[Dict[str, Any]]) -> int:
        """Import multiple clips within a single database transaction for maximum speed"""
        with self._lock:
            conn = self._get_connection()
            count = 0
            with conn:
                cursor = conn.cursor()
                for clip in clips:
                    encrypted_data = clip.get('encrypted_data')
                    if isinstance(encrypted_data, str) and encrypted_data:
                        try:
                            encrypted_data = base64.b64decode(encrypted_data.encode('ascii'))
                        except Exception:
                            pass
                    cursor.execute('''
                        INSERT INTO clips 
                        (content, category, timestamp, is_pinned, is_favorite, encrypted_data, is_encrypted)
                        VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, ?, ?, ?)
                    ''', (
                        clip.get('content', ''),
                        clip.get('category', 'text'),
                        clip.get('timestamp'),
                        clip.get('is_pinned', 0),
                        clip.get('is_favorite', 0),
                        encrypted_data,
                        clip.get('is_encrypted', 0)
                    ))
                    count += 1
            self._bump_version()
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about clipboard collection"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM clips')
            total = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM clips WHERE is_pinned = 1')
            pinned = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM clips WHERE is_favorite = 1')
            favorites = cursor.fetchone()[0]

            cursor.execute('SELECT category, COUNT(*) FROM clips GROUP BY category')
            category_counts = dict(cursor.fetchall())

            db_size = 0
            if os.path.exists(self.db_path):
                db_size = os.path.getsize(self.db_path)

            return {
                'total_clips': total,
                'pinned_clips': pinned,
                'favorite_clips': favorites,
                'categories': category_counts,
                'db_size_bytes': db_size,
                'db_path': self.db_path
            }

    def close(self):
        """Close database connection"""
        with self._lock:
            if self.connection:
                try:
                    self.connection.close()
                except Exception:
                    pass
                self.connection = None
