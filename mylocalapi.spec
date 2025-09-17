# -*- mode: python ; coding: utf-8 -*-
#
# MyLocalAPI PyInstaller spec
# Author: Aidan Paetsch
# Date: 2025-09-15
# License: See LICENSE (GNU GPL v3.0)
# Disclaimer: Provided AS IS. See README.md 'AS IS Disclaimer' for details.
#
import os
import sys
from pathlib import Path

# Get the directory containing this spec file. When PyInstaller runs the spec
# it usually defines __file__, but when executed via some programmatic APIs
# __file__ may be missing. Fall back to the current working directory in that
# case so the spec still resolves relative paths correctly.
try:
    spec_dir = Path(__file__).parent
except NameError:
    import os
    import sys
    # Fallback: prefer the directory of the spec on argv[0] if present, else cwd
    argv0 = Path(sys.argv[0]) if len(sys.argv) > 0 else None
    if argv0 and argv0.exists():
        spec_dir = argv0.parent.resolve()
    else:
        spec_dir = Path(os.getcwd()).resolve()

# Data files to include
datas = []

# Add bundled scripts directory (svcl.exe, etc.)
scripts_dir = spec_dir / 'scripts'
if scripts_dir.exists():
    datas.append((str(scripts_dir), 'scripts'))

# Add icon files
icon_files = ['assets/images/MyLocalAPI_app_icon_new.ico', 'assets/images/mylocalapiappicon.png', 'assets/images/systemtrayicon.png']
for icon_file in icon_files:
    icon_path = spec_dir / icon_file
    if icon_path.exists():
        datas.append((str(icon_path), '.'))

# Add theme files from assets/themes/
theme_dir = spec_dir / 'assets' / 'themes'
if theme_dir.exists():
    datas.append((str(theme_dir), 'assets/themes'))

# Add static files (endpoints.json, etc.)
static_dir = spec_dir / 'static'
if static_dir.exists():
    datas.append((str(static_dir), 'static'))

# Add assets/images directory
images_dir = spec_dir / 'assets' / 'images'
if images_dir.exists():
    datas.append((str(images_dir), 'assets/images'))

# Add sample settings file
sample_settings = spec_dir / 'settings.json'
if sample_settings.exists():
    datas.append((str(sample_settings), '.'))

# Hidden imports - modules that PyInstaller might miss
hiddenimports = [
    'win32gui',
    'win32con', 
    'win32process',
    'win32api',
    'win32event',
    'win32com.shell',
    'win32com.shell.shell',
    'pywintypes',
    'pystray._win32',
    'pickle',
    'PIL._tkinter_finder',
    'requests.packages.urllib3',
    'psutil',
    'customtkinter',
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'flask',
    'flask_cors',
    'werkzeug',
    'werkzeug.serving',
    'jinja2',
    'markupsafe',
    'itsdangerous',
    'click',
    'blinker',
    # Gaming and audio control modules
    'src.gaming_control',
    'src.audio_control', 
    'src.fan_control',
    'src.streaming',
    'src.settings',
    'src.server',
    'src.gui',
    'src.utils'
]

# Collect all Python files
a = Analysis(
    ['src/main.py'],
    pathex=[str(spec_dir), str(spec_dir / 'src')],
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
        'xmlrpc',
        'xml.etree',
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
    icon=str(spec_dir / 'assets' / 'images' / 'MyLocalAPI_app_icon_new.ico'),  # Use existing icon
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