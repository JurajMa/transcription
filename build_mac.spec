# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for building Transcription Studio on macOS."""

block_cipher = None

a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[
        # IMPORTANT: Before building, download ffmpeg from https://ffmpeg.org/download.html
        # (get the static build for macOS) and place the ffmpeg binary in the project root.
        # Uncomment the line below once ffmpeg is in place:
        # ('ffmpeg', '.'),
    ],
    datas=[
        ('static', 'static'),
        ('transcription', 'transcription'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
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
        'pystray',
        'PIL',
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

app = BUNDLE(
    coll,
    name='TranscriptionStudio.app',
    icon=None,
    bundle_identifier='com.transcriptionstudio.app',
)

