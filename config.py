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

# Communication Default Settings
DEFAULT_COMM_SETTINGS = {
    "port": "COM1",
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",      # N = None, E = Even, O = Odd
    "stopbits": 1,      # 1, 1.5, 2
    "timeout": 1.0,
    "simulator_mode": True,  # Default to simulation mode for safety / ease of testing
    "tester_model": "ng-TTS50-xu",
    
    # Tester B Default settings
    "port_b": "COM2",
    "baudrate_b": 9600,
    "bytesize_b": 8,
    "parity_b": "N",
    "stopbits_b": 1,
    "timeout_b": 1.0,
    "simulator_mode_b": True,
    "tester_model_b": "ng-TTS50-xu",

    # Custom model fields (shared fallback for all slots; per-slot keys use suffix _b, _c, …)
    "custom_model_name": "My Sensor",
    "custom_torque_min": 0.0,
    "custom_torque_max": 50.0,
    "custom_serial_pattern": r"([+-]?\d+\.\d+)\s*Nm",
    "custom_model_name_b": "My Sensor B",
    "custom_torque_min_b": 0.0,
    "custom_torque_max_b": 50.0,
    "custom_serial_pattern_b": r"([+-]?\d+\.\d+)\s*Nm",

    # How many tester slots are configured (minimum 2 = A + B)
    "tester_count": 2
}

# App Info
APP_NAME = "Torque Tester & Calibration System"
VERSION = "1.0.0"
