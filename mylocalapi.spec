# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\aapae\\Documents\\Projects\\MyLocalAPI\\scripts', 'scripts'), ('C:\\Users\\aapae\\Documents\\Projects\\MyLocalAPI\\MyLocalAPI_app_icon_new.ico', '.')],
    hiddenimports=['win32gui', 'win32con', 'win32process', 'win32com.shell', 'pystray._win32', 'PIL._tkinter_finder', 'psutil'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'jupyter', 'notebook', 'IPython', 'test', 'tests', 'unittest', 'xml.etree'],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MyLocalAPI',
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
    version='C:\\Users\\aapae\\Documents\\Projects\\MyLocalAPI\\version_info.py',
    icon=['C:\\Users\\aapae\\Documents\\Projects\\MyLocalAPI\\MyLocalAPI_app_icon_new.ico'],
)
