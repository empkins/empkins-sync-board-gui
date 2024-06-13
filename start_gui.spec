# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

import os
CURR_DIR = os.path.abspath(".")

a = Analysis(
    ['open_sync_board_gui/start_gui.py'],
    pathex=[],
    binaries=[],
    datas=[(f'{CURR_DIR}/open_sync_board_gui/config/*.json', 'config'), (f'{CURR_DIR}/open_sync_board_gui/config/*.ini', 'config')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [('v', None, 'OPTION')],
    name='start_gui',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
