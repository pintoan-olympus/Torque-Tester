import os
import sys
from pathlib import Path

# Resolve BASE_DIR correctly whether running as a Python script or a PyInstaller bundle.
# When frozen (compiled), use the folder containing the .exe so that the database
# and log files are stored next to the executable rather than in a temporary directory.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "torque_tester.db"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "app.log"

# Create directories if they do not exist
LOG_DIR.mkdir(exist_ok=True)

# User Access Levels
ACCESS_OPERATOR = 1
ACCESS_SUPERVISOR = 2
ACCESS_ADMIN = 3

ACCESS_LEVEL_NAMES = {
    ACCESS_OPERATOR: "Operator",
    ACCESS_SUPERVISOR: "Supervisor",
    ACCESS_ADMIN: "Admin"
}

# Test Types
TEST_TYPE_PEAK = "peak"
TEST_TYPE_CLICK = "click"
TEST_TYPE_PRESET = "preset"
TEST_TYPE_BREAKAWAY = "breakaway"
TEST_TYPE_RESIDUAL = "residual"

TEST_TYPES = [
    TEST_TYPE_PEAK,
    TEST_TYPE_CLICK,
    TEST_TYPE_PRESET,
    TEST_TYPE_BREAKAWAY,
    TEST_TYPE_RESIDUAL
]

TEST_TYPE_LABELS = {
    TEST_TYPE_PEAK: "Peak Torque",
    TEST_TYPE_CLICK: "Click Torque",
    TEST_TYPE_PRESET: "Preset Torque",
    TEST_TYPE_BREAKAWAY: "Breakaway Torque",
    TEST_TYPE_RESIDUAL: "Residual Torque"
}

# App Info
APP_NAME = "Torque Tester & Calibration System"
VERSION = "1.5.0"
