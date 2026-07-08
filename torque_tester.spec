# torque_tester.spec
# PyInstaller specification file for Torque Tester & Calibration System (One-File Mode)
# Build with: pyinstaller torque_tester.spec
#
# Output will be a single TorqueTester.exe in the dist/ folder.

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Bundle customtkinter assets (themes, images)
ctk_datas = collect_data_files("customtkinter", include_py_files=False)

# Also include darkdetect assets if present
try:
    dd_datas = collect_data_files("darkdetect", include_py_files=False)
except Exception:
    dd_datas = []

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=ctk_datas + dd_datas,
    hiddenimports=[
        # customtkinter & dependencies
        "customtkinter",
        "customtkinter.windows",
        "customtkinter.windows.widgets",
        "customtkinter.windows.widgets.appearance_mode",
        "darkdetect",
        # PIL / Pillow (used by customtkinter for image rendering)
        "PIL",
        "PIL._tkinter_finder",
        "PIL.Image",
        "PIL.ImageTk",
        # bcrypt
        "bcrypt",
        "bcrypt.hashpw",
        # pyserial
        "serial",
        "serial.tools",
        "serial.tools.list_ports",
        # standard library
        "json",
        "sqlite3",
        "logging",
        "logging.handlers",
        "threading",
        "queue",
        # project modules
        "config",
        "app",
        "auth.login_view",
        "auth.user_manager",
        "database.db_manager",
        "database.models",
        "sensor.sensor_interface",
        "sensor.simulator",
        "sensor.serial_comm",
        "utils.logger",
        "utils.helpers",
        "views.components",
        "views.dashboard",
        "views.driver_manager",
        "views.settings_view",
        "views.test_history",
        "views.test_runner",
        "views.test_setup",
        "views.user_admin",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter.test", "unittest", "email", "html", "http", "urllib", "xml"],
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
    name="TorqueTester",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # No terminal window (GUI mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # Uncomment and add icon file to enable
)
