# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/frontend', 'frontend'),
        ('clipbox.ico', '.'),
    ],
    hiddenimports=[
        'win32clipboard',
        'win32con',
        'cryptography',
        'cryptography.fernet',
        'webview',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6',
        'PySide6',
        'matplotlib',
        'scipy',
        'torch',
        'pandas',
        'tkinter',
        'unittest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ClipBox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='clipbox.ico',
)
