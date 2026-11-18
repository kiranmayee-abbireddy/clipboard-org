# tests/test_e2e_simulation.py
import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from api import ClipboardAPI

def run_simulation():
    print("Starting ClipBox End-to-End Simulation...")
    api = ClipboardAPI(':memory:')
    api.initialize_clipboard_service()

    # 1. Themes
    assert json.loads(api.get_theme_settings())['mode'] == 'light'
    api.set_theme('dark', 'midnight')
    assert json.loads(api.get_theme_settings())['mode'] == 'dark'
    assert json.loads(api.get_theme_settings())['style'] == 'midnight'

    # 2. Categories
    cat_info = json.loads(api.get_category_info())
    for cat in ['url', 'email', 'phone', 'password', 'code', 'text']:
        assert cat in cat_info
        assert 'color' in cat_info[cat]
        assert 'icon' in cat_info[cat]

    cat_settings = json.loads(api.get_category_settings())
    assert cat_settings['phone'] is True
    api.set_category_enabled('phone', False)
    assert json.loads(api.get_category_settings())['phone'] is False

    # 3. Add Clips
    assert api.manual_add_clip('https://antigravity.google.com/docs', 'url') is True
    assert api.manual_add_clip('user@gmail.com', 'email') is True
    assert api.manual_add_clip('const a = 10;\nconst b = 20;', 'code') is True

    # 4. Search
    res_search = json.loads(api.search_clips('antigravity'))
    assert len(res_search) >= 1
    assert 'antigravity' in res_search[0]['content']

    # 5. Pinned / Favorite
    clip_id = res_search[0]['id']
    assert api.toggle_pin(clip_id) is True
    assert api.toggle_favorite(clip_id) is True

    # 6. Passwords & Encryption
    assert api.is_passkey_set() is False
    assert api.setup_passkey('masterkey123') is True
    assert api.is_passkey_set() is True
    assert api.is_password_locked() is False

    # Add password while unlocked
    api.manual_add_clip('MySecretPass#2026', 'password')
    clips = json.loads(api.get_all_clips())
    pwd_clip = next(c for c in clips if c['category'] == 'password')
    assert pwd_clip['content'] == 'MySecretPass#2026'

    # Lock passwords
    api.lock_passwords()
    assert api.is_password_locked() is True
    clips_locked = json.loads(api.get_all_clips())
    pwd_clip_locked = next(c for c in clips_locked if c['category'] == 'password')
    assert pwd_clip_locked['content'] == '[Encrypted Password]'

    # Unlock passwords
    assert api.verify_passkey('wrongpass') is False
    assert api.verify_passkey('masterkey123') is True
    assert api.is_password_locked() is False

    # 7. Update Clip Content
    assert api.update_clip_content(clip_id, 'https://antigravity.google.com/updated') is True
    updated = json.loads(api.get_clip_by_id(clip_id))
    assert updated['content'] == 'https://antigravity.google.com/updated'

    # 8. Copy Clip
    assert api.copy_clip(clip_id) is True

    # 9. Import Clips
    export_json = api.export_clips()
    assert isinstance(export_json, str)
    import_result = api.import_clips(json.dumps([
        {'content': 'Imported Clip 1', 'category': 'text'},
        {'content': 'Imported Clip 2', 'category': 'url'}
    ]))
    assert import_result['status'] == 'success'
    assert import_result['count'] == 2

    # 10. Stats
    stats = json.loads(api.get_app_stats())
    assert stats['total_clips'] >= 6
    assert stats['pinned_clips'] >= 1

    api.shutdown()
    print("Simulation completed with 100% success!")

if __name__ == '__main__':
    run_simulation()
