import time
import random
import math
import threading
from utils.logger import get_logger
from sensor.sensor_interface import TorqueSensorInterface

logger = get_logger()

class TorqueSensorSimulator(TorqueSensorInterface):
    def __init__(self):
        self._lock = threading.Lock()
        self._connected = False
        self._peak_torque = 0.0
        self._cycle_start_time = None
        self._cycle_duration = 2.0  # seconds
        self._cycle_target = 0.0
        self._is_in_cycle = False

    def connect(self) -> bool:
        with self._lock:
            logger.info("Simulator: Connecting to virtual torque sensor...")
            self._connected = True
            self._peak_torque = 0.0
            logger.info("Simulator: Connected to virtual torque sensor (ng-TTS50-xu Simulated)")
            return True

    def disconnect(self) -> None:
        with self._lock:
            logger.info("Simulator: Disconnecting virtual sensor...")
            self._connected = False
            self._is_in_cycle = False

    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    def start_torque_cycle(self, target_value: float, duration: float = 2.0):
        """Trigger a simulated torque push peaking at target_value."""
        with self._lock:
            if not self._connected:
                return
            self._cycle_target = target_value
            self._cycle_duration = duration
            self._cycle_start_time = time.time()
            self._is_in_cycle = True
            logger.debug(f"Simulator: Started torque cycle targeting {target_value} cNm")

    def read_torque(self) -> float:
        """Returns instantaneous torque in cNm."""
        with self._lock:
            if not self._connected:
                return 0.0

            current_time = time.time()

            if self._is_in_cycle and self._cycle_start_time:
                elapsed = current_time - self._cycle_start_time
                if elapsed < self._cycle_duration:
                    # Use a sine wave shape to simulate ramping up and ramping down
                    phase = (elapsed / self._cycle_duration) * math.pi
                    base_val = math.sin(phase) * self._cycle_target
                    
                    # Add random noise (up to 3% of target value)
                    noise = (random.random() - 0.5) * 0.06 * self._cycle_target
                    val = max(0.0, base_val + noise)
                else:
                    self._is_in_cycle = False
                    val = (random.random() - 0.5) * 0.1  # Residual noise after cycle
            else:
                # Idle noise around zero
                val = (random.random() - 0.5) * 0.1

            # Keep values within sensor bounds (-50 cNm to 50 cNm)
            val = max(-50.0, min(50.0, val))

            # Update peak torque
            if val > self._peak_torque:
                self._peak_torque = val

            return round(val, 2)

    def get_peak(self) -> float:
        with self._lock:
            if not self._connected:
                return 0.0
            return round(self._peak_torque, 2)

    def reset_peak(self) -> None:
        with self._lock:
            if self._connected:
                logger.debug("Simulator: Reset peak torque")
                self._peak_torque = 0.0

    def get_status_info(self) -> dict:
        with self._lock:
            return {
                "device": "ng-TTS50-xu (Simulated)",
                "connection_type": "Virtual COM Loopback",
                "firmware_version": "v1.0.0-sim",
                "torque_range": "±50 cNm",
                "status": "OPERATIONAL" if self._connected else "OFFLINE"
            }
