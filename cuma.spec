# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

# CUMA 1.100.12
# Dados editáveis do usuário não são empacotados como JSONs soltos.
# O app cria/usa %APPDATA%\CUMA\cuma_settings.json quando compilado.
datas = [
    ('cuma_settings_template.json', '.'),
    ('cuma_logo.png', '.'),
    ('app_icon.ico', '.'),
]
try:
    datas += collect_data_files('tkinterdnd2')
except Exception:
    pass

a = Analysis(
    ['cuma.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PIL._tkinter_finder', 'fitz', 'numpy', 'tkinterdnd2'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cuma',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='app_icon.ico',
)

# Atualizador externo em modo standalone.
# Ele é copiado para %TEMP% antes de rodar, permitindo substituir também
# o cuma_updater.exe da pasta instalada.
updater_a = Analysis(
    ['cuma_updater.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['tkinter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
updater_pyz = PYZ(updater_a.pure, updater_a.zipped_data)
updater_exe = EXE(
    updater_pyz,
    updater_a.scripts,
    updater_a.binaries,
    updater_a.zipfiles,
    updater_a.datas,
    [],
    name='cuma_updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    updater_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CUMA_windows',
)
