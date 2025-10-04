# clipboard_organizer.spec
block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('src/frontend', 'frontend')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    name='ClipBox',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)

# No COLLECT step here for pure onefile mode
