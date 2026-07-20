import os
import configparser
from pathlib import Path
import config
from utils.logger import get_logger

logger = get_logger()

DEFAULT_VALUES = {
    "port": "COM1",
    "baudrate": 9600,
    "bytesize": 8,
    "parity": "N",
    "stopbits": 1,
    "timeout": 1.0,
    "simulator_mode": True,
    "tester_model": "ng-TTS50-xu",
    "custom_model_name": "My Sensor",
    "custom_torque_min": 0.0,
    "custom_torque_max": 50.0,
    "custom_serial_pattern": r"([+-]?\d+\.\d+)\s*Nm",
    "tester_count": 2
}

class HardwareConfig:
    def __init__(self, filepath=None):
        if filepath is None:
            # Save hardware.ini next to config.py (in BASE_DIR)
            self.filepath = Path(config.BASE_DIR) / "hardware.ini"
        else:
            self.filepath = Path(filepath)
            
        self.parser = configparser.ConfigParser()
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                self.parser.read(self.filepath, encoding="utf-8")
                logger.info(f"Loaded hardware config from {self.filepath}")
            except (configparser.Error, OSError) as e:
                logger.error(f"Error reading hardware config {self.filepath}: {e}")
                self.create_default_config()
        else:
            self.create_default_config()

    def save(self):
        try:
            # Ensure directory exists
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                self.parser.write(f)
            logger.info(f"Saved hardware config to {self.filepath}")
        except OSError as e:
            logger.error(f"Error saving hardware config {self.filepath}: {e}")

    def create_default_config(self):
        logger.info("Creating default hardware config file")
        self.parser.clear()
        
        # General section
        self.parser["general"] = {
            "tester_count": "2"
        }
        
        # Core Tester A
        self.parser["tester_a"] = {
            "port": "COM1",
            "baudrate": "9600",
            "bytesize": "8",
            "parity": "N",
            "stopbits": "1",
            "timeout": "1.0",
            "simulator_mode": "true",
            "tester_model": "ng-TTS50-xu",
            "custom_model_name": "My Sensor",
            "custom_torque_min": "0.0",
            "custom_torque_max": "50.0",
            "custom_serial_pattern": r"([+-]?\d+\.\d+)\s*Nm"
        }
        
        # Core Tester B
        self.parser["tester_b"] = {
            "port": "COM2",
            "baudrate": "9600",
            "bytesize": "8",
            "parity": "N",
            "stopbits": "1",
            "timeout": "1.0",
            "simulator_mode": "true",
            "tester_model": "ng-TTS50-xu",
            "custom_model_name": "My Sensor B",
            "custom_torque_min": "0.0",
            "custom_torque_max": "50.0",
            "custom_serial_pattern": r"([+-]?\d+\.\d+)\s*Nm"
        }
        
        self.save()

    def _resolve_key(self, flat_key: str) -> tuple[str, str]:
        """Maps flat key like 'port_b' or 'custom_torque_max_c' to (section, actual_key)."""
        if flat_key == "tester_count":
            return "general", "tester_count"
        if flat_key == "language":
            return "app", "language"
            
        # Check suffixes like _b, _c, ..., _h
        for i in range(1, 8):  # b is index 1, c is 2, ..., h is 7
            suffix = f"_{chr(97 + i)}"
            if flat_key.endswith(suffix):
                actual_key = flat_key[:-len(suffix)]
                section = f"tester_{chr(97 + i)}"
                return section, actual_key
                
        # Suffix is empty (Tester A)
        return "tester_a", flat_key

    def get_setting(self, flat_key: str, default=None):
        section, key = self._resolve_key(flat_key)
        
        if not self.parser.has_section(section) or not self.parser.has_option(section, key):
            # Fallback to local default mapping
            if flat_key == "tester_count":
                return 2
                
            if key in DEFAULT_VALUES:
                # Handle ordinal-based COM ports dynamic resolution (COM1, COM2, COM3, ...)
                if key == "port" and section.startswith("tester_"):
                    char_idx = ord(section[7]) - ord('a') + 1
                    return f"COM{char_idx}"
                # Handle custom model names dynamic resolution (My Sensor, My Sensor B, My Sensor C, ...)
                if key == "custom_model_name" and section.startswith("tester_"):
                    char = section[7].upper()
                    return f"My Sensor" if char == 'A' else f"My Sensor {char}"
                return DEFAULT_VALUES[key]
                
            return default
            
        val_str = self.parser.get(section, key)
        
        # Try to infer correct type
        # 1. Boolean
        if val_str.lower() in ("true", "yes", "on", "1"):
            return True
        if val_str.lower() in ("false", "no", "off", "0"):
            return False
            
        # 2. Integer
        try:
            return int(val_str)
        except ValueError:
            pass
            
        # 3. Float
        try:
            return float(val_str)
        except ValueError:
            pass
            
        # 4. String
        return val_str

    def set_setting(self, flat_key: str, value) -> bool:
        section, key = self._resolve_key(flat_key)
        
        if not self.parser.has_section(section):
            self.parser.add_section(section)
            
        # Convert values to strings
        if isinstance(value, bool):
            val_str = "true" if value else "false"
        else:
            val_str = str(value)
            
        self.parser.set(section, key, val_str)
        self.save()
        return True

    def get_all_settings(self) -> dict:
        """Returns a flat dictionary matching key:value structure for SettingsView caching."""
        flat = {}
        for section in self.parser.sections():
            prefix = ""
            if section.startswith("tester_"):
                letter = section.split("_")[1]  # 'a', 'b', 'c', etc.
                if letter != "a":
                    prefix = f"_{letter}"
                    
            for key, val in self.parser.items(section):
                # Map booleans, ints, floats where possible
                typed_val = val
                if val.lower() in ("true", "yes", "on"):
                    typed_val = True
                elif val.lower() in ("false", "no", "off"):
                    typed_val = False
                else:
                    try:
                        typed_val = int(val)
                    except ValueError:
                        try:
                            typed_val = float(val)
                        except ValueError:
                            pass
                
                if section == "general":
                    flat[key] = typed_val
                else:
                    flat[f"{key}{prefix}"] = typed_val
        return flat

    def delete_settings_for_tester(self, suffix: str) -> bool:
        """Deletes section for tester e.g. tester_c for suffix _c."""
        if not suffix.startswith("_") or len(suffix) < 2:
            return False
        letter = suffix[1].lower()
        section = f"tester_{letter}"
        if self.parser.has_section(section):
            self.parser.remove_section(section)
            self.save()
            return True
        return False
