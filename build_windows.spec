# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for building Transcription Studio on Windows."""

block_cipher = None

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[
        # IMPORTANT: Before building, download ffmpeg.exe from https://ffmpeg.org/download.html
        # and place it in the project root directory.
        # Uncomment the line below once ffmpeg.exe is in place:
        ('ffmpeg.exe', '.'),
    ],
    datas=[
        ('static', 'static'),
        ('transcription', 'transcription'),
    ],
    hiddenimports=[
        'audioop',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TranscriptionStudio',
    icon='icon.ico', 
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode - no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TranscriptionStudio',
)
