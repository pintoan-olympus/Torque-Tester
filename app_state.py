from dataclasses import dataclass, field
from typing import Optional
from database.models import TorqueDriver, TestDefinition, TestBattery, BatteryItem

@dataclass
class AppState:
    """Centralized, typed state container for current operator session and active test selections."""
    selected_workbench: str = ""
    selected_driver: Optional[TorqueDriver] = None
    selected_test_def: Optional[TestDefinition] = None
    selected_battery: Optional[TestBattery] = None
    battery_items: list[BatteryItem] = field(default_factory=list)
    current_battery_step: int = 0
    battery_session_id: Optional[int] = None

    def reset_session_selections(self):
        """Reset active selections after a test session completes."""
        self.selected_driver = None
        self.selected_test_def = None
        self.selected_battery = None
        self.battery_items.clear()
        self.current_battery_step = 0
        self.battery_session_id = None
