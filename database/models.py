from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
import datetime

@dataclass
class User:
    id: Optional[int] = None
    username: str = ""
    password_hash: str = ""
    full_name: str = ""
    access_level: int = 1  # 1: Operator, 2: Supervisor, 3: Admin
    active: bool = True
    created_at: Optional[str] = None

@dataclass
class TorqueDriver:
    id: Optional[int] = None
    driver_id: str = ""  # Unique string identifier
    driver_type: str = ""
    brand: str = ""
    model: str = ""
    torque_min: float = 0.0
    torque_max: float = 0.0
    workbench: str = ""
    calibration_date: Optional[str] = None
    calibration_due: Optional[str] = None
    notes: str = ""
    active: bool = True
    default_test_def_id: Optional[int] = None
    handedness: str = "right"

@dataclass
class TestDefinition:
    id: Optional[int] = None
    name: str = ""
    test_type: str = "peak"
    target_value: float = 0.0
    tolerance_plus: float = 0.0
    tolerance_minus: float = 0.0
    num_samples: int = 5
    min_samples: int = 3
    min_ok_samples: Optional[int] = None
    default_tester_id: str = "A"
    instructions: str = ""
    active: bool = True

@dataclass
class TestSession:
    id: Optional[int] = None
    driver_id: int = 0
    test_def_id: int = 0
    workbench: str = ""
    operator_id: int = 0
    started_at: str = ""
    completed_at: Optional[str] = None
    overall_result: str = "ABORTED"  # PASS, FAIL, ABORTED

@dataclass
class TestMeasurement:
    id: Optional[int] = None
    session_id: int = 0
    sample_number: int = 0
    measured_value: float = 0.0
    result: str = "NOK"  # OK, NOK
    timestamp: str = ""

@dataclass
class TestBattery:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    active: bool = True

@dataclass
class BatteryItem:
    id: Optional[int] = None
    battery_id: int = 0
    test_def_id: int = 0
    sequence_order: int = 0
    test_def: Optional[TestDefinition] = None  # populated by JOIN query
