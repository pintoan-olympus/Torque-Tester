import os
import sys
from enum import IntEnum, Enum
from pathlib import Path

# Resolve BASE_DIR correctly whether running as a Python script or a PyInstaller bundle.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "torque_tester.db"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "app.log"

# Create directories if they do not exist
LOG_DIR.mkdir(exist_ok=True)

# --- User Access Levels ---
class AccessLevel(IntEnum):
    OPERATOR = 1
    SUPERVISOR = 2
    ADMIN = 3

ACCESS_OPERATOR = AccessLevel.OPERATOR.value
ACCESS_SUPERVISOR = AccessLevel.SUPERVISOR.value
ACCESS_ADMIN = AccessLevel.ADMIN.value

ACCESS_LEVEL_NAMES = {
    AccessLevel.OPERATOR: "Operator",
    AccessLevel.SUPERVISOR: "Supervisor",
    AccessLevel.ADMIN: "Admin"
}

# --- Test Types ---
class TestType(str, Enum):
    PEAK = "peak"
    CLICK = "click"
    PRESET = "preset"
    BREAKAWAY = "breakaway"
    RESIDUAL = "residual"

TEST_TYPE_PEAK = TestType.PEAK.value
TEST_TYPE_CLICK = TestType.CLICK.value
TEST_TYPE_PRESET = TestType.PRESET.value
TEST_TYPE_BREAKAWAY = TestType.BREAKAWAY.value
TEST_TYPE_RESIDUAL = TestType.RESIDUAL.value

TEST_TYPES = [t.value for t in TestType]

TEST_TYPE_LABELS = {
    TestType.PEAK.value: "Peak Torque",
    TestType.CLICK.value: "Click Torque",
    TestType.PRESET.value: "Preset Torque",
    TestType.BREAKAWAY.value: "Breakaway Torque",
    TestType.RESIDUAL.value: "Residual Torque"
}

# --- Configurable Thresholds & Intervals ---
WRONG_TESTER_THRESHOLD_CNM = 2.0
AUTO_CAPTURE_SNAPBACK_RATIO = 0.85
AUTO_CAPTURE_MIN_DELTA_CNM = 0.5
ROTATION_DIRECTION_THRESHOLD_CNM = 0.15
STATUS_BAR_POLL_INTERVAL_MS = 2000
SENSOR_POLL_INTERVAL_MS = 50

# --- App Info ---
APP_NAME = "Torque Tester & Calibration System"
VERSION = "1.5.0"

