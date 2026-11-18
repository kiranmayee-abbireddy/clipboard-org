# tests/test_backend.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from backend.database import ClipboardDatabase
from backend.categorizer import ContentCategorizer
from backend.crypto_handler import CryptoHandler

def test_database():
    db = ClipboardDatabase(':memory:')
    c1 = db.add_clip('Test Clip 1', 'text')
    c2 = db.add_clip('https://example.com', 'url')
    assert db.get_clip_by_id(c1)['content'] == 'Test Clip 1'
    assert len(db.get_all_clips()) == 2
    assert db.toggle_pin(c1) is True
    assert db.get_clip_by_id(c1)['is_pinned'] == 1
    assert db.toggle_favorite(c1) is True
    
    # bump_or_add_clip
    id_bump, is_new = db.bump_or_add_clip('Test Clip 1', 'text')
    assert is_new is False
    assert id_bump == c1
    
    # stats
    stats = db.get_stats()
    assert stats['total_clips'] == 2
    assert stats['pinned_clips'] == 1
    
    # cleanup
    db.connection.execute("UPDATE clips SET timestamp = datetime('now', '-35 days') WHERE id = ?", (c2,))
    db.connection.commit()
    deleted = db.cleanup_old_clips(30)
    assert deleted == 1
    assert len(db.get_all_clips()) == 1
    
    # batch import
    clips_batch = [
        {'content': 'item 1', 'category': 'text'},
        {'content': 'item 2', 'category': 'url'},
    ]
    imported = db.import_clips_batch(clips_batch)
    assert imported == 2
    assert len(db.get_all_clips()) == 3
    db.close()
    print("Database tests passed!")

def test_crypto():
    handler = CryptoHandler('test_passkey_123')
    enc = handler.encrypt('secret password')
    dec = handler.decrypt(enc)
    assert dec == 'secret password'
    
    b64 = handler.encrypt_to_b64('another secret')
    assert handler.decrypt(b64) == 'another secret'
    print("Crypto tests passed!")

def test_categorizer():
    assert ContentCategorizer.categorize('https://antigravity.google.com') == 'url'
    assert ContentCategorizer.categorize('contact@domain.com') == 'email'
    assert ContentCategorizer.categorize('+91 98765 43210') == 'phone'
    assert ContentCategorizer.categorize('sk-ant-test12345') == 'password'
    assert ContentCategorizer.categorize('def calculate_total(a, b):\n    return a + b') == 'code'
    assert ContentCategorizer.categorize('Simple plain text note') == 'text'
    print("Categorizer tests passed!")

if __name__ == '__main__':
    test_database()
    test_crypto()
    test_categorizer()
    print("All backend tests completed successfully!")
