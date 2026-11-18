# tests/test_api.py
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api import ClipboardAPI

def test_api():
    api = ClipboardAPI(':memory:')
    api.initialize_clipboard_service()
    
    # 1. Manual add
    res = api.manual_add_clip('https://github.com', 'url')
    assert res is True
    
    # 2. Get all clips
    clips_json = api.get_all_clips()
    clips = json.loads(clips_json)
    assert len(clips) == 1
    clip_id = clips[0]['id']
    
    # 3. Toggle pin & favorite
    assert api.toggle_pin(clip_id) is True
    assert api.toggle_favorite(clip_id) is True
    
    # 4. Search clips
    search_json = api.search_clips('github')
    search_results = json.loads(search_json)
    assert len(search_results) == 1
    
    # 5. Version check
    v1 = api.get_clips_version()
    api.manual_add_clip('second clip', 'text')
    v2 = api.get_clips_version()
    assert v2 > v1
    
    # 6. Passkey setup and unlock
    assert api.is_passkey_set() is False
    assert api.setup_passkey('secret123') is True
    assert api.is_passkey_set() is True
    assert api.is_password_locked() is False
    
    # Add password clip while unlocked
    api.manual_add_clip('my_bank_pwd', 'password')
    all_clips = json.loads(api.get_all_clips())
    pwd_clip = next(c for c in all_clips if c['category'] == 'password')
    # Because unlocked, content is decrypted
    assert pwd_clip['content'] == 'my_bank_pwd'
    
    # Lock passwords
    api.lock_passwords()
    assert api.is_password_locked() is True
    all_clips_locked = json.loads(api.get_all_clips())
    pwd_clip_locked = next(c for c in all_clips_locked if c['category'] == 'password')
    assert pwd_clip_locked['content'] == '[Encrypted Password]'
    
    # Unlock passwords
    assert api.verify_passkey('secret123') is True
    assert api.is_password_locked() is False
    
    # 7. Category info
    cat_info = json.loads(api.get_category_info())
    assert 'url' in cat_info
    assert 'code' in cat_info
    
    # 8. Stats
    stats = json.loads(api.get_app_stats())
    assert stats['total_clips'] >= 3
    
    # 9. Export to file test
    export_file = api.export_clips_to_file()
    assert os.path.exists(export_file)
    os.remove(export_file)
    
    api.shutdown()
    print("All ClipboardAPI tests passed successfully!")

if __name__ == '__main__':
    test_api()
