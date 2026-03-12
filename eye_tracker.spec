# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect mediapipe data
mp_datas, mp_binaries, mp_hiddenimports = collect_all('mediapipe')

# Collect cv2 data
cv2_datas = collect_data_files('cv2')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=mp_binaries,
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('images', 'images'),
        ('aoi_config_per_image.json', '.'),
        ('aoi_config.json', '.'),
    ] + mp_datas + cv2_datas,
    hiddenimports=[
        'cv2',
        'numpy',
        'PIL',
        'flask',
        'jinja2',
        'werkzeug',
        'mediapipe',
        'mediapipe.tasks',
        'mediapipe.tasks.python',
        'mediapipe.tasks.python.vision',
        'mediapipe.tasks.python.vision.face_landmarker',
        'mediapipe.tasks.python.core',
        'mediapipe.tasks.python.core.base_options',
        'mediapipe.python',
        'mediapipe.python._framework_bindings',
        'keyboard',
        'pywin32',
        'win32api',
        'win32con',
    ] + mp_hiddenimports,
    hookspath=['.'],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='EyeTracker',
    debug=False,
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
    icon=None,
)
