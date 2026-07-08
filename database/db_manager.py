import sqlite3
import json
import datetime
from pathlib import Path
from typing import Optional
import config
from utils.logger import get_logger
from database.models import User, TorqueDriver, TestDefinition, TestSession, TestMeasurement

logger = get_logger()


class DatabaseManager:
    def __init__(self, db_path=None, config_path="db_config.json"):
        self.config_path = config_path
        self._settings_cache: dict = {}   # In-memory cache – cleared on set_setting()
        self.load_db_config(db_path)
        self.init_db()

    def load_db_config(self, db_path=None):
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.db_config = json.load(f)
            else:
                self.db_config = {
                    "db_type": "sqlite",
                    "sqlite_path": db_path or str(config.DB_PATH),
                    "sql_server_conn_str": ""
                }
                self.save_db_config()
        except Exception as e:
            logger.error(f"Error loading database config: {e}")
            self.db_config = {
                "db_type": "sqlite",
                "sqlite_path": db_path or str(config.DB_PATH),
                "sql_server_conn_str": ""
            }

    def save_db_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.db_config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving database config: {e}")

    def get_connection(self):
        db_type = self.db_config.get("db_type", "sqlite")
        if db_type == "sql_server":
            try:
                import pyodbc
            except ImportError:
                raise ImportError(
                    "The 'pyodbc' library is required to connect to SQL Server.\n"
                    "Please run: pip install pyodbc"
                )

            conn_str = self.db_config.get("sql_server_conn_str", "")
            # Automatically translate ADO.NET syntax (like Data Source=...) to ODBC connection string
            if conn_str and "driver" not in conn_str.lower():
                parts = {}
                for p in conn_str.split(";"):
                    if "=" in p:
                        k, v = p.split("=", 1)
                        parts[k.strip().lower()] = v.strip()
                
                server = parts.get("data source")
                database = parts.get("initial catalog")
                uid = parts.get("user id") or parts.get("user-id") or parts.get("uid")
                pwd = parts.get("password") or parts.get("pwd")
                
                if server and database:
                    driver = "{ODBC Driver 17 for SQL Server}"
                    conn_str = f"Driver={driver};Server={server};Database={database};"
                    if uid:
                        conn_str += f"Uid={uid};"
                    if pwd:
                        conn_str += f"Pwd={pwd};"

            conn = pyodbc.connect(conn_str)
            
            # Map standard row factory or Row class for pyodbc to match sqlite Row dictionary lookup
            class PyODBCRowWrapper:
                def __init__(self, row, columns):
                    self.row = row
                    self.columns = columns
                    # Build O(1) lookup dict once at construction time
                    self._col_index = {c: i for i, c in enumerate(columns)}
                    self._col_index_lower = {c.lower(): i for i, c in enumerate(columns)}
                def __getitem__(self, key):
                    if isinstance(key, int):
                        return self.row[key]
                    if key in self._col_index:
                        return self.row[self._col_index[key]]
                    lk = key.lower()
                    if lk in self._col_index_lower:
                        return self.row[self._col_index_lower[lk]]
                    raise KeyError(key)
                def keys(self):
                    return self.columns
                    
            class PyODBCCursorWrapper:
                def __init__(self, cursor):
                    self.cursor = cursor
                def execute(self, sql, params=None):
                    sql_clean = sql
                    # Catch and ignore VACUUM for SQL Server
                    if sql_clean.strip().upper() == "VACUUM":
                        return self
                        
                    # Translate SQLite specific CREATE TABLE constraints
                    sql_clean = sql_clean.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "INT IDENTITY(1,1) PRIMARY KEY")
                    sql_clean = sql_clean.replace("TEXT UNIQUE", "VARCHAR(255) UNIQUE")
                    sql_clean = sql_clean.replace("TEXT", "VARCHAR(MAX)")
                    sql_clean = sql_clean.replace("DATETIME DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT GETDATE()")
                    sql_clean = sql_clean.replace("CURRENT_TIMESTAMP", "GETDATE()")
                    sql_clean = sql_clean.replace("BOOLEAN DEFAULT 1", "BIT DEFAULT 1")
                    sql_clean = sql_clean.replace("BOOLEAN DEFAULT 0", "BIT DEFAULT 0")
                    sql_clean = sql_clean.replace("BOOLEAN", "BIT")
                    sql_clean = sql_clean.replace("ADD COLUMN", "ADD")
                    
                    # Intercept SQLite INSERT OR REPLACE to SQL Server UPDATE/INSERT fallback
                    if "INSERT OR REPLACE INTO app_settings" in sql_clean:
                        sql_clean = """
                        UPDATE app_settings SET value = ? WHERE [key] = ?
                        IF @@ROWCOUNT = 0
                        INSERT INTO app_settings ([key], value) VALUES (?, ?)
                        """
                        if params and len(params) == 2:
                            k, v = params[0], params[1]
                            params = [v, k, k, v]
                            
                    # Translate SQLite CREATE TABLE IF NOT EXISTS
                    if "CREATE TABLE IF NOT EXISTS" in sql_clean:
                        import re
                        match = re.search(r"CREATE TABLE IF NOT EXISTS\s+(\w+)", sql_clean, re.IGNORECASE)
                        if match:
                            tbl = match.group(1)
                            body = sql_clean[match.end():].strip()
                            sql_clean = f"""
                            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{tbl}' AND xtype='U')
                            BEGIN
                                CREATE TABLE {tbl} {body}
                            END
                            """

                    if params:
                        # Convert boolean values to integers (0 or 1) because SQL Server BIT expects integer/bit, not bool
                        clean_params = []
                        for val in params:
                            if isinstance(val, bool):
                                clean_params.append(1 if val else 0)
                            else:
                                clean_params.append(val)
                        self.cursor.execute(sql_clean, clean_params)
                    else:
                        self.cursor.execute(sql_clean)
                    return self
                def fetchone(self):
                    row = self.cursor.fetchone()
                    if row:
                        cols = [col[0] for col in self.cursor.description]
                        return PyODBCRowWrapper(row, cols)
                    return None
                def fetchall(self):
                    rows = self.cursor.fetchall()
                    cols = [col[0] for col in self.cursor.description]
                    return [PyODBCRowWrapper(r, cols) for r in rows]
                @property
                def lastrowid(self):
                    self.cursor.execute("SELECT SCOPE_IDENTITY()")
                    row = self.cursor.fetchone()
                    if row and row[0] is not None:
                        return int(row[0])
                    return None
                    
            class PyODBCConnectionWrapper:
                def __init__(self, conn):
                    self.conn = conn
                def cursor(self):
                    return PyODBCCursorWrapper(self.conn.cursor())
                def commit(self):
                    self.conn.commit()
                def close(self):
                    self.conn.close()
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc_val, exc_tb):
                    if exc_type is not None:
                        self.conn.rollback()
                    else:
                        self.conn.commit()
                    self.conn.close()
                    
            return PyODBCConnectionWrapper(conn)
        else:
            conn = sqlite3.connect(self.db_config.get("sqlite_path", str(config.DB_PATH)))
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn

    def init_db(self):
        """Create tables if they do not exist."""
        db_type = self.db_config.get("db_type", "sqlite")
        logger.info(f"Initializing database ({db_type}) path/string: {self.db_config.get('sqlite_path') or self.db_config.get('sql_server_conn_str')}")
        
        # Check and migrate settings from database to hardware.ini if app_settings exists
        migrate_settings = False
        settings_to_migrate = {}
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if db_type == "sql_server":
                    cursor.execute("SELECT * FROM sysobjects WHERE name='app_settings' AND xtype='U'")
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_settings'")
                if cursor.fetchone():
                    migrate_settings = True
                    cursor.execute("SELECT [key], [value] FROM app_settings")
                    for row in cursor.fetchall():
                        settings_to_migrate[row["key"]] = json.loads(row["value"])
        except Exception as e:
            logger.error(f"Error checking app_settings table for migration: {e}")

        if migrate_settings:
            logger.info("Found app_settings table in DB. Migrating values to hardware.ini...")
            try:
                from hardware_config import HardwareConfig
                hw_config = HardwareConfig()
                for key, val in settings_to_migrate.items():
                    hw_config.set_setting(key, val)
                
                # Now drop the table
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DROP TABLE app_settings")
                    conn.commit()
                logger.info("Migrated settings to hardware.ini and dropped app_settings table successfully.")
            except Exception as e:
                logger.error(f"Error migrating settings from DB: {e}")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    access_level INTEGER NOT NULL,
                    active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Torque Drivers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS torque_drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id TEXT UNIQUE NOT NULL,
                    driver_type TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    torque_min REAL NOT NULL,
                    torque_max REAL NOT NULL,
                    workbench TEXT NOT NULL,
                    calibration_date DATE,
                    calibration_due DATE,
                    notes TEXT,
                    active BOOLEAN DEFAULT 1,
                    default_test_def_id INTEGER,
                    handedness TEXT DEFAULT 'right'
                )
            """)

            # Test Definitions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    test_type TEXT NOT NULL,
                    target_value REAL NOT NULL,
                    tolerance_plus REAL NOT NULL,
                    tolerance_minus REAL NOT NULL,
                    num_samples INTEGER DEFAULT 5,
                    min_samples INTEGER DEFAULT 3,
                    min_ok_samples INTEGER,
                    default_tester_id TEXT DEFAULT 'A',
                    instructions TEXT,
                    active BOOLEAN DEFAULT 1
                )
            """)

            # Run schema migrations for existing databases
            try:
                cursor.execute("ALTER TABLE torque_drivers ADD COLUMN default_test_def_id INTEGER")
                logger.info("Database migration: Added default_test_def_id column to torque_drivers table")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE torque_drivers ADD COLUMN handedness TEXT DEFAULT 'right'")
                logger.info("Database migration: Added handedness column to torque_drivers table")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE test_definitions ADD COLUMN min_samples INTEGER DEFAULT 3")
                logger.info("Database migration: Added min_samples column to test_definitions table")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE test_definitions ADD COLUMN min_ok_samples INTEGER")
                logger.info("Database migration: Added min_ok_samples column to test_definitions table")
            except Exception:
                pass

            try:
                cursor.execute("ALTER TABLE test_definitions ADD COLUMN default_tester_id TEXT DEFAULT 'A'")
                logger.info("Database migration: Added default_tester_id column to test_definitions table")
            except Exception:
                pass

            # Test Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER NOT NULL,
                    test_def_id INTEGER NOT NULL,
                    workbench TEXT NOT NULL,
                    operator_id INTEGER NOT NULL,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    overall_result TEXT DEFAULT 'ABORTED',
                    FOREIGN KEY(driver_id) REFERENCES torque_drivers(id),
                    FOREIGN KEY(test_def_id) REFERENCES test_definitions(id),
                    FOREIGN KEY(operator_id) REFERENCES users(id)
                )
            """)

            # Test Measurements table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    sample_number INTEGER NOT NULL,
                    measured_value REAL NOT NULL,
                    result TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(session_id) REFERENCES test_sessions(id)
                )
            """)
            
            # Seed default torque driver if empty
            cursor.execute("SELECT COUNT(*) FROM torque_drivers")
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding default torque driver (DRV-001)")
                today = datetime.date.today().isoformat()
                next_year = (datetime.date.today() + datetime.timedelta(days=365)).isoformat()
                cursor.execute(
                    """INSERT INTO torque_drivers 
                       (driver_id, driver_type, brand, model, torque_min, torque_max, workbench, calibration_date, calibration_due, notes, active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("DRV-001", "Electric", "Atlas Copco", "MTFocus-60", 5.0, 50.0, "Assembly Bench 1", today, next_year, "Default setup driver.", 1)
                )

            # Seed default test definition if empty
            cursor.execute("SELECT COUNT(*) FROM test_definitions")
            if cursor.fetchone()[0] == 0:
                logger.info("Seeding default test definition")
                cursor.execute(
                    """INSERT INTO test_definitions 
                       (name, test_type, target_value, tolerance_plus, tolerance_minus, num_samples, instructions, active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("Standard Click Test 30 cNm", "click", 30.0, 3.0, 3.0, 5, 
                     "1. Insert the tool bit into the ng-TTS50-xu torque sensor.\n2. Gently apply force in the clockwise direction.\n3. Continue applying force slowly until a click/slip is felt.\n4. Disengage force, reset peak, and proceed to the next sample.\n5. Complete 5 samples.", 1)
                )
            
            conn.commit()

    # --- User Operations ---
    
    def create_user(self, user: User) -> bool:
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

    def get_user_by_username(self, username: str) -> Optional[User]:
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

    def get_all_users(self) -> list[User]:
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

    def update_user(self, user: User) -> bool:
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
            logger.error(f"Error updating user: {e}")
            return False

    # --- Torque Driver Operations ---
    
    def create_driver(self, driver: TorqueDriver) -> Optional[int]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                def_test = driver.default_test_def_id if driver.default_test_def_id != 0 else None
                hand = getattr(driver, 'handedness', 'right')
                cursor.execute(
                    """INSERT INTO torque_drivers 
                       (driver_id, driver_type, brand, model, torque_min, torque_max, workbench, calibration_date, calibration_due, notes, active, default_test_def_id, handedness)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (driver.driver_id, driver.driver_type, driver.brand, driver.model,
                     driver.torque_min, driver.torque_max, driver.workbench,
                     driver.calibration_date, driver.calibration_due, driver.notes, driver.active, def_test, hand)
                )
                conn.commit()
                new_id = cursor.lastrowid
                logger.info(f"Driver created: {driver.driver_id} with ID {new_id}")
                return new_id
        except Exception as e:
            logger.error(f"Error creating driver: {e}")
            return None

    def get_driver_by_tag(self, driver_id_str: str) -> Optional[TorqueDriver]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM torque_drivers WHERE driver_id = ?", (driver_id_str,))
                row = cursor.fetchone()
                if row:
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
                        default_test_def_id=row["default_test_def_id"] or 0,
                        handedness=row["handedness"] if "handedness" in row.keys() else "right"
                    )
        except Exception as e:
            logger.error(f"Error fetching driver by tag {driver_id_str}: {e}")
        return None

    def get_all_drivers(self) -> list[TorqueDriver]:
        drivers = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM torque_drivers ORDER BY driver_id ASC")
                for row in cursor.fetchall():
                    drivers.append(TorqueDriver(
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
                        default_test_def_id=row["default_test_def_id"] or 0,
                        handedness=row["handedness"] if "handedness" in row.keys() else "right"
                    ))
        except Exception as e:
            logger.error(f"Error fetching all drivers: {e}")
        return drivers

    def update_driver(self, driver: TorqueDriver) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                def_test = driver.default_test_def_id if driver.default_test_def_id != 0 else None
                hand = getattr(driver, 'handedness', 'right')
                cursor.execute(
                    """UPDATE torque_drivers 
                       SET driver_id = ?, driver_type = ?, brand = ?, model = ?, 
                           torque_min = ?, torque_max = ?, workbench = ?, 
                           calibration_date = ?, calibration_due = ?, notes = ?, active = ?, default_test_def_id = ?, handedness = ?
                       WHERE id = ?""",
                    (driver.driver_id, driver.driver_type, driver.brand, driver.model,
                     driver.torque_min, driver.torque_max, driver.workbench,
                     driver.calibration_date, driver.calibration_due, driver.notes, driver.active, def_test, hand, driver.id)
                )
                conn.commit()
                logger.info(f"Driver updated: {driver.driver_id}")
                return True
        except Exception as e:
            logger.error(f"Error updating driver: {e}")
            return False

    # --- Test Definition Operations ---
    
    def create_test_definition(self, test_def: TestDefinition) -> Optional[int]:
        try:
            min_ok = test_def.min_ok_samples if test_def.min_ok_samples is not None else test_def.min_samples
            tester_id = getattr(test_def, 'default_tester_id', 'A')
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO test_definitions 
                       (name, test_type, target_value, tolerance_plus, tolerance_minus, num_samples, min_samples, min_ok_samples, default_tester_id, instructions, active)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (test_def.name, test_def.test_type, test_def.target_value, test_def.tolerance_plus,
                     test_def.tolerance_minus, test_def.num_samples, test_def.min_samples, min_ok, tester_id, test_def.instructions, test_def.active)
                )
                conn.commit()
                new_id = cursor.lastrowid
                logger.info(f"Test Definition created: {test_def.name} with ID {new_id}")
                return new_id
        except Exception as e:
            logger.error(f"Error creating test definition: {e}")
            return None

    def get_all_test_definitions(self) -> list[TestDefinition]:
        templates = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM test_definitions ORDER BY name ASC")
                for row in cursor.fetchall():
                    templates.append(TestDefinition(
                        id=row["id"],
                        name=row["name"],
                        test_type=row["test_type"],
                        target_value=row["target_value"],
                        tolerance_plus=row["tolerance_plus"],
                        tolerance_minus=row["tolerance_minus"],
                        num_samples=row["num_samples"],
                        min_samples=row["min_samples"] if "min_samples" in row.keys() else 3,
                        min_ok_samples=row["min_ok_samples"] if "min_ok_samples" in row.keys() else (row["min_samples"] if "min_samples" in row.keys() else 3),
                        default_tester_id=row["default_tester_id"] if "default_tester_id" in row.keys() else 'A',
                        instructions=row["instructions"],
                        active=bool(row["active"])
                    ))
        except Exception as e:
            logger.error(f"Error fetching all test definitions: {e}")
        return templates

    def update_test_definition(self, test_def: TestDefinition) -> bool:
        try:
            min_ok = test_def.min_ok_samples if test_def.min_ok_samples is not None else test_def.min_samples
            tester_id = getattr(test_def, 'default_tester_id', 'A')
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE test_definitions 
                       SET name = ?, test_type = ?, target_value = ?, tolerance_plus = ?, 
                           tolerance_minus = ?, num_samples = ?, min_samples = ?, min_ok_samples = ?, default_tester_id = ?, instructions = ?, active = ?
                       WHERE id = ?""",
                    (test_def.name, test_def.test_type, test_def.target_value, test_def.tolerance_plus,
                     test_def.tolerance_minus, test_def.num_samples, test_def.min_samples, min_ok,
                     tester_id, test_def.instructions, test_def.active, test_def.id)
                )
                conn.commit()
                logger.info(f"Test Definition updated: {test_def.name}")
                return True
        except Exception as e:
            logger.error(f"Error updating test definition: {e}")
            return False

    # --- Test Session and Measurement Operations ---
    
    def start_test_session(self, driver_id: int, test_def_id: int, workbench: str, operator_id: int) -> Optional[int]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO test_sessions (driver_id, test_def_id, workbench, operator_id, overall_result)
                       VALUES (?, ?, ?, ?, 'ABORTED')""",
                    (driver_id, test_def_id, workbench, operator_id)
                )
                conn.commit()
                session_id = cursor.lastrowid
                logger.info(f"Test session {session_id} started for driver {driver_id}")
                return session_id
        except Exception as e:
            logger.error(f"Error starting test session: {e}")
            return None

    def add_measurement(self, session_id: int, sample_number: int, measured_value: float, result: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO test_measurements (session_id, sample_number, measured_value, result)
                       VALUES (?, ?, ?, ?)""",
                    (session_id, sample_number, measured_value, result)
                )
                conn.commit()
                logger.debug(f"Measurement added to session {session_id}: Sample {sample_number} = {measured_value} ({result})")
                return True
        except Exception as e:
            logger.error(f"Error adding measurement: {e}")
            return False

    def complete_test_session(self, session_id: int, overall_result: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE test_sessions 
                       SET completed_at = CURRENT_TIMESTAMP, overall_result = ?
                       WHERE id = ?""",
                    (overall_result, session_id)
                )
                conn.commit()
                logger.info(f"Test session {session_id} completed with result: {overall_result}")
                return True
        except Exception as e:
            logger.error(f"Error completing test session: {e}")
            return False

    def get_test_history(self, driver_id_str: str = None, workbench: str = None, result: str = None) -> list[dict]:
        """Fetch joined history data for presentation."""
        history = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT ts.id as session_id, ts.started_at, ts.completed_at, ts.overall_result, ts.workbench,
                           td.driver_id as driver_id_str, td.brand, td.model,
                           tdef.name as test_name, tdef.target_value,
                           u.full_name as operator_name
                    FROM test_sessions ts
                    JOIN torque_drivers td ON ts.driver_id = td.id
                    JOIN test_definitions tdef ON ts.test_def_id = tdef.id
                    JOIN users u ON ts.operator_id = u.id
                """
                params = []
                conditions = []
                
                if driver_id_str:
                    conditions.append("td.driver_id LIKE ?")
                    params.append(f"%{driver_id_str}%")
                if workbench:
                    conditions.append("ts.workbench LIKE ?")
                    params.append(f"%{workbench}%")
                if result:
                    conditions.append("ts.overall_result = ?")
                    params.append(result)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                
                query += " ORDER BY ts.started_at DESC"
                
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    history.append(dict(row))
        except Exception as e:
            logger.error(f"Error fetching test history: {e}")
        return history

    def get_measurements_for_session(self, session_id: int) -> list[dict]:
        measurements = []
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM test_measurements WHERE session_id = ? ORDER BY sample_number ASC",
                    (session_id,)
                )
                for row in cursor.fetchall():
                    measurements.append(dict(row))
        except Exception as e:
            logger.error(f"Error fetching measurements: {e}")
        return measurements
    # --- Settings Operations have been migrated to hardware_config.py ---

    def get_session_by_id(self, session_id: int) -> Optional[dict]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT ts.id as session_id, ts.started_at, ts.completed_at, ts.overall_result, ts.workbench,
                           td.driver_id as driver_id_str, td.brand, td.model,
                           tdef.name as test_name, tdef.target_value, tdef.tolerance_plus, tdef.tolerance_minus,
                           u.full_name as operator_name
                    FROM test_sessions ts
                    JOIN torque_drivers td ON ts.driver_id = td.id
                    JOIN test_definitions tdef ON ts.test_def_id = tdef.id
                    JOIN users u ON ts.operator_id = u.id
                    WHERE ts.id = ?
                """
                cursor.execute(query, (session_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.error(f"Error fetching session by id {session_id}: {e}")
        return None

    def export_table_to_csv(self, table_name: str, file_path: str) -> bool:
        try:
            import csv
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                headers = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                     writer = csv.writer(f)
                     writer.writerow(headers)
                     for row in rows:
                         writer.writerow([row[k] for k in headers])
            return True
        except Exception as e:
            logger.error(f"Error exporting table {table_name} to csv: {e}")
            return False

    def import_table_from_csv(self, table_name: str, file_path: str) -> dict:
        import csv
        stats = {"added": 0, "updated": 0, "failed": 0}
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    
                    for row in reader:
                        try:
                            if table_name == "torque_drivers":
                                cursor.execute("SELECT id FROM torque_drivers WHERE driver_id = ?", (row["driver_id"],))
                                exists = cursor.fetchone()
                                if exists:
                                    cols = [f"{k} = ?" for k in row.keys() if k != "id" and k != "driver_id"]
                                    vals = [row[k] for k in row.keys() if k != "id" and k != "driver_id"]
                                    vals.append(row["driver_id"])
                                    cursor.execute(f"UPDATE torque_drivers SET {', '.join(cols)} WHERE driver_id = ?", vals)
                                    stats["updated"] += 1
                                else:
                                    cols = [k for k in row.keys() if k != "id"]
                                    vals = [row[k] for k in cols]
                                    placeholders = ", ".join(["?"] * len(cols))
                                    cursor.execute(f"INSERT INTO torque_drivers ({', '.join(cols)}) VALUES ({placeholders})", vals)
                                    stats["added"] += 1
                                    
                            elif table_name == "test_definitions":
                                cursor.execute("SELECT id FROM test_definitions WHERE name = ?", (row["name"],))
                                exists = cursor.fetchone()
                                if exists:
                                    cols = [f"{k} = ?" for k in row.keys() if k != "id" and k != "name"]
                                    vals = [row[k] for k in row.keys() if k != "id" and k != "name"]
                                    vals.append(row["name"])
                                    cursor.execute(f"UPDATE test_definitions SET {', '.join(cols)} WHERE name = ?", vals)
                                    stats["updated"] += 1
                                else:
                                    cols = [k for k in row.keys() if k != "id"]
                                    vals = [row[k] for k in cols]
                                    placeholders = ", ".join(["?"] * len(cols))
                                    cursor.execute(f"INSERT INTO test_definitions ({', '.join(cols)}) VALUES ({placeholders})", vals)
                                    stats["added"] += 1
                        except Exception as item_err:
                            logger.error(f"Error importing row {row} in {table_name}: {item_err}")
                            stats["failed"] += 1
                conn.commit()
        except Exception as e:
            logger.error(f"Error importing table {table_name} from csv: {e}")
            stats["failed"] += 1
        return stats

    def reset_all_test_data(self, backup_file_path: str) -> tuple[bool, str]:
        """Backs up all test sessions and measurements to CSV, then deletes all records from the tables."""
        import csv
        try:
            # 1. Fetch all data
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT ts.id as session_id, ts.started_at, ts.completed_at, ts.overall_result, ts.workbench,
                           td.driver_id as driver_id_str, td.brand, td.model,
                           tdef.name as test_name, tdef.target_value,
                           u.full_name as operator_name,
                           tm.sample_number, tm.measured_value, tm.result as sample_result, tm.timestamp as sample_timestamp
                    FROM test_sessions ts
                    JOIN torque_drivers td ON ts.driver_id = td.id
                    JOIN test_definitions tdef ON ts.test_def_id = tdef.id
                    JOIN users u ON ts.operator_id = u.id
                    JOIN test_measurements tm ON tm.session_id = ts.id
                    ORDER BY ts.started_at ASC, tm.sample_number ASC
                """
                cursor.execute(query)
                rows = cursor.fetchall()
                
                # Write to CSV
                headers = [
                    "Session ID", "Started At", "Completed At", "Overall Result", "Workbench",
                    "Driver ID", "Brand", "Model", "Test Procedure", "Target (cNm)",
                    "Operator", "Sample Number", "Measured Value (cNm)", "Sample Result", "Sample Timestamp"
                ]
                
                with open(backup_file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Torque Tester System - All Historical Test Records Reset Backup"])
                    writer.writerow([])
                    writer.writerow(headers)
                    for r in rows:
                        writer.writerow([
                            r["session_id"], r["started_at"], r["completed_at"], r["overall_result"], r["workbench"],
                            r["driver_id_str"], r["brand"], r["model"], r["test_name"], f"{r['target_value']:.2f}",
                            r["operator_name"], r["sample_number"], f"{r['measured_value']:.2f}", r["sample_result"], r["sample_timestamp"]
                        ])
            
            # 2. Perform table clears
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM test_measurements")
                cursor.execute("DELETE FROM test_sessions")
                cursor.execute("VACUUM")
                conn.commit()
                
            return True, f"Successfully backed up {len(rows)} records and cleared all test history tables."
        except Exception as e:
            logger.error(f"Error resetting all test data: {e}")
            return False, str(e)
