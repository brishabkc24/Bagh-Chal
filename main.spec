# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build for Bagh Chal.
#
#   Build:   python -m PyInstaller main.spec --noconfirm --clean
#   Output:  dist\BaghChal.exe   (single file, no console window)
#
# The four PNG images are bundled next to the code; gui.resource_path() finds
# them inside the bundle via sys._MEIPASS, so the .exe runs from any folder.

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('goat.png', '.'),
        ('tiger.png', '.'),
        ('inner_board.png', '.'),
        ('outer_bg.jpg', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BaghChal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
