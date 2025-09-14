# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the directory containing this spec file
spec_dir = Path(__file__).parent

# Data files to include
datas = []

# Add bundled scripts directory (svcl.exe, etc.)
scripts_dir = spec_dir / 'scripts'
if scripts_dir.exists():
    datas.append((str(scripts_dir), 'scripts'))

# Add sample settings file
sample_settings = spec_dir / 'settings.json'
if sample_settings.exists():
    datas.append((str(sample_settings), '.'))

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'win32gui',
    'win32con', 
    'win32process',
    'win32com.shell',
    'win32com.shell.shell',
    'pystray._win32',
    'PIL._tkinter_finder',
    'requests.packages.urllib3',
    'psutil'
]

# Collect all Python files
a = Analysis(
    ['main.py'],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
        'test',
        'tests',
        'testing',
        'unittest',
        'doctest',
        'pdb',
        'difflib',
        'email',
        'http.server',
        'urllib.request',
        'urllib.parse',
        'xmlrpc',
        'xml.etree',
        'pickle',
        'pickletools'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate entries
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MyLocalAPI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',  # Optional version info file
    icon='icon.ico',  # Optional icon file
)

# Alternative: Create directory-based distribution instead of single file
# Uncomment the following for a directory distribution:

# exe = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name='MyLocalAPI',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     console=False,
# )
# 
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name='MyLocalAPI',
# )