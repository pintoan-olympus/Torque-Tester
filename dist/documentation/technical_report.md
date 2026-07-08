# Technical Report: Torque Tester & Calibration System

This report outlines the technical design, architectural patterns, database schemas, local settings separation, hardware integration protocols, and optimization decisions implemented for the **Torque Tester & Calibration System**.

---

## 1. Executive Summary
The Torque Tester & Calibration System is a high-reliability desktop application engineered for industrial tool auditing and peak-torque tracking. The system communicates via serial lines to high-precision rotary torque sensors, processes real-time scientific data feeds, provides visual tolerance evaluations, and audits historical compliance logs. Key achievements include decoupling machine-local configurations from database schemas, integrating dynamic multi-sensor tabs, implementing snap-back automatic peak holding, and providing multi-tier access clearance.

---

## 2. Decoupled Architecture
The codebase follows a decoupled Model-View-Controller (MVC) approach, enforcing modular separation between data, presentation, and hardware control:

### Architectural Components
1.  **Entry Point (`main.py`)**: Resolves platform execution paths, initializes monitor DPI settings, boots database connections, hashes default credentials, and starts the CustomTkinter event queue thread.
2.  **App Shell (`app.py`)**: Acts as the main controller. It controls dynamic view loading, lazy screen rendering, sidebar routing navigation, global status updates, and handles background sensor threads reconnect.
3.  **Local settings managers**:
    *   **`hardware_config.py` (`hardware.ini`)**: Manages physical interface settings (COM ports, baud rates, simulator modes, tester models, and custom serial parse regexes) on a per-device level. Decoupled from the database to prevent settings pollution on shared databases.
    *   **`db_config.json`**: Connects the app to either local SQLite files or remote Microsoft SQL Server connection strings.
4.  **Database Manager (`db_manager.py`)**: Executes relational migrations and hosts operational data (Users, Driver specifications, Test procedures, Sessions, and Measurements).
5.  **Hardware communication layer (`sensor/`)**: Implements standard interface methods (`connect()`, `disconnect()`, `read_torque()`, `get_peak()`, `reset_peak()`) across simulated and physical serially connected models.

---

## 3. Separation of Configuration Storage
To facilitate zero-loss database switching (local SQLite ↔ online SQL Server) and avoid machine-specific details polluting a central shared database, configurations are cleanly separated:

### File-System Storage Details
-   **`db_config.json`**:
    *   *Path*: Root next to the executable.
    *   *Keys*: `db_type`, `sqlite_path`, `sql_server_conn_str`.
-   **`hardware.ini`**:
    *   *Path*: Root next to the executable.
    *   *Structure*: INI file format.
    *   *Sections*:
        *   `[general]`: `tester_count` (active sensor slots).
        *   `[tester_a]`, `[tester_b]`, `[tester_c]`, etc.: Contains ports, baudrates, databits, stopbits, parity, timeout, simulator toggle, model description, custom bounds (`custom_torque_min`, `custom_torque_max`), and custom serial reader regex (`custom_serial_pattern`).

### Zero-Touch Settings Migration
On initial boot, the app executes a schema migration. If an `app_settings` table is found inside the database:
1.  The database query reads all stored keys.
2.  The settings are populated into the machine-local `hardware.ini` file.
3.  The database table `app_settings` is dropped, keeping the DB clean and local configurations private to the machine.

---

## 4. Sensor Interface & Protocol Parsing
The physical hardware interface parses newline-terminated streams from RS-232/USB emulator ports.

### Scientific Stream Parser
-   **Standard `ng-TTS50-xu` Mode**: Reads raw bytes and detects control delimiters (STX `0x06` / ETX `0x08`). Extracts active mode characters and reads a 10-character scientific notation value (e.g. `+08021E-05 Nm`), automatically scaling it by `100.0` to Centinewton-meters (`8.02 cNm`).
-   **Custom Regex Mode**: Allows administrators to specify custom regex matching rules (e.g. `([+-]?\d+\.\d+)\s*Nm`). The parser continuously reads lines, extracts the first matching capture group, and scales it to `cNm`.

### Visual Needle Gauge
The Test Runner incorporates a CustomTkinter-drawn visual dial gauge. It dynamically parses the active tester's limits from `hardware.ini` to establish its maximum indicator range (e.g., up to `50.0 cNm` for TTS50, or `500.0 cNm` for TTS500).

---

## 5. Peak Capture State Machine (Snap-Back)
To capture clutch-click torque peaks accurately without requiring manual operator intervention, the system runs a 3-state machine:

```
      +------------+      Torque > Start Threshold      +------------+
      |    IDLE    | ---------------------------------> |   RISING   |
      +------------+                                    +------------+
            ^                                                  |
            |                                                  | Torque drops by 15%
            |                                                  | AND absolute drop >= 0.5 cNm
            |                                                  v
            |             Torque < Reset Threshold      +------------+
            +------------------------------------------ |  CAPTURED  |
                                                        +------------+
```

-   **Start Threshold**: `max(0.5, 0.15 * target_value)`
-   **Reset Threshold**: `max(0.3, 0.08 * target_value)`
-   **Snap-Back Drop Criteria**: `current_torque < peak_torque * 0.85` AND `peak_torque - current_torque >= 0.5 cNm`
-   **State Transitioning**: Safely resets to `IDLE` once the operator disengages the tool and torque falls below the reset threshold, preventing duplicate sample logs during a single clutch slip cycle.

---

## 6. Relational Database Design
Decoupled schema definitions allow the database system to migrate and save compliance audits:

```
      +-----------------+          +----------------------+
      |      users      |          |    torque_drivers    |
      +-----------------+          +----------------------+
      | id (PK)         |          | id (PK)              |
      | username        |          | driver_id (UQ)       |
      | password_hash   |          | driver_type          |
      | full_name       |          | brand, model         |
      | access_level    | <---+    | torque_min, max      |
      | active, created |     |    | workbench            |
      +-----------------+     |    | calibration_date/due |
                              |    | default_test_def_id  | ---> [test_definitions]
                              |    | handedness           |
      +-----------------+     |    +----------------------+
      |  test_sessions  |     |               |
      +-----------------+     |               v
      | id (PK)         |     |      (Session logs)
      | driver_id (FK)  | ----+---------------+
      | test_def_id (FK)|                     |
      | workbench       |                     v
      | operator_id (FK)| ---------> [test_measurements]
      | started_at      |            - id (PK)
      | completed_at    |            - session_id (FK)
      | overall_result  |            - sample_number
      +-----------------+            - measured_value (signed negative for CCW)
                                     - result (OK/NOK)
```

---

## 7. Performance & Optimization Highlights
1.  **Lazy Renders**: Screens and views are dynamically generated and cached at the moment of access, minimizing load times and system RAM consumption on startup.
2.  **Threaded Serial Pollers**: Hardware serial read loops run inside separate background daemon threads, avoiding Tkinter main-loop UI freezing and guaranteeing high-frequency torque updates (150ms intervals).
3.  **Tail Log File Reader**: The settings page loads only the final 16 KB segment of the system log file to prevent file read delays on large production logging logs.
4.  **SQL Server Row wrappers**: The DB manager incorporates a custom connection wrapper translating Sqlite Row dictionaries to pyodbc column queries transparently, enabling 100% codebase compatibility.
