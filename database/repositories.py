from typing import Optional, Callable
from database.models import (
    User, TorqueDriver, TestDefinition, TestSession,
    TestMeasurement, TestBattery, BatteryItem
)
from utils.logger import get_logger

logger = get_logger()


class UserRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def create(self, user: User) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO users (username, password_hash, full_name, access_level, active)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user.username, user.password_hash, user.full_name, user.access_level, user.active)
                )
                conn.commit()
                logger.info(f"User created: {user.username}")
                return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    def get_by_username(self, username: str) -> Optional[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row["id"],
                        username=row["username"],
                        password_hash=row["password_hash"],
                        full_name=row["full_name"],
                        access_level=row["access_level"],
                        active=bool(row["active"])
                    )
        except Exception as e:
            logger.error(f"Error fetching user by username {username}: {e}")
        return None

    def get_by_id(self, user_id: int) -> Optional[User]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return User(
                        id=row["id"],
                        username=row["username"],
                        password_hash=row["password_hash"],
                        full_name=row["full_name"],
                        access_level=row["access_level"],
                        active=bool(row["active"])
                    )
        except Exception as e:
            logger.error(f"Error fetching user by id {user_id}: {e}")
        return None

    def get_all(self) -> list[User]:
        users = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY username ASC")
                for row in cursor.fetchall():
                    users.append(User(
                        id=row["id"],
                        username=row["username"],
                        password_hash=row["password_hash"],
                        full_name=row["full_name"],
                        access_level=row["access_level"],
                        active=bool(row["active"])
                    ))
        except Exception as e:
            logger.error(f"Error fetching all users: {e}")
        return users

    def update(self, user: User) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE users 
                       SET username = ?, password_hash = ?, full_name = ?, access_level = ?, active = ?
                       WHERE id = ?""",
                    (user.username, user.password_hash, user.full_name, user.access_level, user.active, user.id)
                )
                conn.commit()
                logger.info(f"User updated: {user.username}")
                return True
        except Exception as e:
            logger.error(f"Error updating user {user.username}: {e}")
            return False


class DriverRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def create(self, driver: TorqueDriver) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO torque_drivers 
                       (driver_id, driver_type, brand, model, torque_min, torque_max, 
                        workbench, calibration_date, calibration_due, notes, active, default_test_def_id, default_battery_id, handedness)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (driver.driver_id, driver.driver_type, driver.brand, driver.model,
                     driver.torque_min, driver.torque_max, driver.workbench,
                     driver.calibration_date, driver.calibration_due, driver.notes,
                     driver.active, driver.default_test_def_id, driver.default_battery_id,
                     driver.handedness)
                )
                conn.commit()
                logger.info(f"Driver created: {driver.driver_id}")
                return True
        except Exception as e:
            logger.error(f"Error creating driver {driver.driver_id}: {e}")
            return False

    def get_by_tag(self, tag: str) -> Optional[TorqueDriver]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM torque_drivers WHERE driver_id = ?", (tag,))
                row = cursor.fetchone()
                if row:
                    return self._map_row(row)
        except Exception as e:
            logger.error(f"Error fetching driver by tag {tag}: {e}")
        return None

    def get_all(self) -> list[TorqueDriver]:
        drivers = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM torque_drivers ORDER BY driver_id ASC")
                for row in cursor.fetchall():
                    drivers.append(self._map_row(row))
        except Exception as e:
            logger.error(f"Error fetching all drivers: {e}")
        return drivers

    def update(self, driver: TorqueDriver) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE torque_drivers 
                       SET driver_type = ?, brand = ?, model = ?, torque_min = ?, torque_max = ?, 
                           workbench = ?, calibration_date = ?, calibration_due = ?, notes = ?, active = ?,
                           default_test_def_id = ?, default_battery_id = ?, handedness = ?
                       WHERE driver_id = ?""",
                    (driver.driver_type, driver.brand, driver.model, driver.torque_min, driver.torque_max,
                     driver.workbench, driver.calibration_date, driver.calibration_due, driver.notes, driver.active,
                     driver.default_test_def_id, driver.default_battery_id, driver.handedness,
                     driver.driver_id)
                )
                conn.commit()
                logger.info(f"Driver updated: {driver.driver_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating driver {driver.driver_id}: {e}")
            return False

    def delete(self, driver_id_str: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM torque_drivers WHERE driver_id = ?", (driver_id_str,))
                conn.commit()
                logger.info(f"Driver deleted: {driver_id_str}")
                return True
        except Exception as e:
            logger.error(f"Error deleting driver {driver_id_str}: {e}")
            raise e

    def _map_row(self, row) -> TorqueDriver:
        return TorqueDriver(
            id=row["id"],
            driver_id=row["driver_id"],
            driver_type=row["driver_type"],
            brand=row["brand"],
            model=row["model"],
            torque_min=row["torque_min"],
            torque_max=row["torque_max"],
            workbench=row["workbench"],
            calibration_date=row["calibration_date"],
            calibration_due=row["calibration_due"],
            notes=row["notes"],
            active=bool(row["active"]),
            default_test_def_id=row["default_test_def_id"] if "default_test_def_id" in row.keys() else None,
            default_battery_id=row["default_battery_id"] if "default_battery_id" in row.keys() else None,
            handedness=row["handedness"] if "handedness" in row.keys() else "right"
        )
