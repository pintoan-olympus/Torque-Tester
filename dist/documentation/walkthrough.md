# Torque Tester Application Walkthrough

The **Torque Tester Application** is fully implemented and verified. It is located in the workspace directory at [C:\Users\pintoan\.gemini\antigravity\scratch\torque_tester](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester).

---

## 🚀 Getting Started

### 1. Prerequisites
Verify that you have the required dependencies. They have been installed, but if you change environments you can re-run:
```bash
pip install -r requirements.txt
```

### 2. Launching the App
Run the entry point script using Python:
```bash
python main.py
```

### 3. Default Login Credentials
Upon the first run, the database is seeded with a default **Administrator** account:
*   **Username**: `admin`
*   **Password**: `admin`

> [!IMPORTANT]
> Because the administrator has access to settings, user management, and databases, you should change the password or deactivate this default account in the **User Admin** panel once production accounts are set up.

---

## 🛠️ Application Design & Features

### 🔐 3-Level Access Control System
1.  **Operator (Level 1)**:
    *   Initialize and run tests.
    *   View testing history and detailed measurement records.
    *   View hardware parameters (read-only).
2.  **Supervisor (Level 2)**:
    *   All Operator capabilities.
    *   Manage the Torque Driver database registry.
    *   Manage standard test procedure templates (target, tolerances, quantities, and instructions).
3.  **Admin (Level 3)**:
    *   All Supervisor capabilities.
    *   Full user account control (create, lock, level-assignment, password resets).
    *   Modify hardware communication parameters (ports, baudrates, bits) and toggle simulator mode.

---

## 📐 Components and View Files

Here are links to the primary code modules:

*   [config.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/config.py): Contains global constants, error codes, and hardware default parameters.
*   [main.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/main.py): Entry-point initializing SQLite, hashing strategies, theme settings, and Tkinter thread.
*   [app.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/app.py): Application shell handling sidebar navigation, lazy screen renders, status bar bindings, and sensor reconnects.
*   [database/db_manager.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/database/db_manager.py): Active database manager managing SQLite connections, relational schemas, history logging, and settings tables.
*   [sensor/simulator.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/sensor/simulator.py): Active simulator class generating realistic torque curves (using math sine formulas), peak holding, and target noise.
*   [sensor/serial_comm.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/sensor/serial_comm.py): Physical serial interface utilizing `pyserial` with an ASCII parser to read numeric torque readouts from the virtual or physical COM port.
*   [views/components.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/views/components.py): Reusable UI widgets including the **TorqueGauge** (renders live dial, peak tick, target zones, and status colors) and the **ScrollableTable**.
*   [views/test_runner.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/views/test_runner.py): Core test execution view with live polling, capture triggers, sample discards, and auto-logging.
*   [views/settings_view.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/views/settings_view.py): Config panel with test routines, hardware toggles, and log viewer loading files from `logs/app.log`.

---

## 📊 Database Schema Setup

The app automatically builds a relational schema in SQLite (`torque_tester.db`) on startup:

*   **`users`**: Contains credential hashes, display names, activation states, and privilege levels.
*   **`torque_drivers`**: Registry of torque drivers (ID, type, range, assigned workbench, calibration history, calibration due warnings).
*   **`test_definitions`**: Templates defining procedures, targets, upper/lower tolerances, sample quantities, and custom guidelines.
*   **`test_sessions`**: Record of overall test runs (operator, driver, workbench, started, completed, overall result: PASS/FAIL/ABORTED).
*   **`test_measurements`**: Holds individual measurement entries for each session sample.
*   **`app_settings`**: Key-value settings store for hardware serial configuration.

---

## 🔬 Verification Logs

A validation script ([verify_imports.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/verify_imports.py)) was executed to verify module dependency paths and integrity.

**Result Output**:
```text
Verifying imports for Torque Tester modules...
[OK] config imported
[OK] database.models imported
[OK] database.db_manager imported
[OK] auth.user_manager imported
[OK] utils.logger imported
[OK] utils.helpers imported
[OK] sensor.sensor_interface imported
[OK] sensor.simulator imported
[OK] sensor.serial_comm imported
[OK] auth.login_view imported
[OK] views.components imported
[OK] views.dashboard imported
[OK] views.test_runner imported
[OK] views.test_history imported
[OK] views.driver_manager imported
[OK] views.test_setup imported
[OK] views.user_admin imported
[OK] views.settings_view imported
[OK] app imported

SUCCESS: All modules imported successfully without errors!
```

---

## 🔬 Verification Logs

We have verified the newly added capabilities:
1. **Auto Capture Peak (on Snap-Back)**:
   - Evaluated by monitoring the instantaneous torque read loop.
   - Triggers automatically upon detecting a torque value drop (15% drop from the tracked peak and at least 0.5 cNm drop) once torque rises above 15% of the target value.
   - Safely transitions states (`IDLE` -> `RISING` -> `CAPTURED` -> `IDLE` when torque returns to rest) to prevent duplicate triggers on a single click/slip cycle.
   
2. **Minimum Number of Tests Configuration**:
   - The **Test Setup** view now lets supervisors set both "Quantity of measurements (Max Samples)" and "Minimum measurements (Min Samples)" (with validation: `min_samples <= max_samples`).
   - The database maps the `min_samples` column.
   - The **Test Runner** disables the "Finish Test" action until at least `min_samples` tests are successfully recorded. Once reached, the operator can manually finalize the session with a green PASS/FAIL evaluation early, or continue to maximum samples for auto-completion.

3. **Default Test in Driver configuration**:
   - The **Driver Registry** now includes a "Default Test Template" selector listing all active test procedures.
   - Selecting a driver in the dashboard initialization screen automatically pre-selects its assigned default test template.

4. **Configurable Minimum OK Samples to Pass**:
   - The **Test Setup** view allows defining a "Minimum OK to Pass (Min OK)" threshold.
   - The **Test Runner** calculates overall pass/fail results by counting total `OK` measurements against `Min OK`.
   - The final session completed label shows the exact passing ratio (e.g. `SESSION COMPLETED: PASS (4/5 OK)`).

5. **Overall Test History CSV Export & DB Import/Export**:
   - An "Export History" button in the Test History filters bar writes a formatted CSV containing all filtered or overall test session records.
   - A dedicated **Data Management** panel under Settings handles exporting and importing full CSV backups of the drivers and templates tables with database upsert matching.

6. **Dual Tester Support**:
   - A tabbed configuration panel manages Tester A and Tester B ports, settings, model descriptions (`ng-TTS50-xu` or `ng-TTS500-xu`), and live previews.
   - Procedures configure default testers. The Test Runner automatically binds the correct sensor, fetches its designated model from DB settings, and displays active tester metadata in the runner info frame.

7. **Driver Handedness (CW / CCW)**:
   - Drivers configure handedness (`Right (CW, +)` / `Left (CCW, -)`).
   - In CCW mode, measurements are sign-flipped to negative values for SQLite storage, while absolute values are evaluated against limits and displayed on the positive 0-to-max needle gauge.

8. **Danger Zone: Reset All Test Records**:
   - A "Reset & Clear All Test Records" action under Settings permits administrators to wipe test session and measurement history.
   - The app enforces an automatic CSV save routine prior to clearing tables to preserve historical data.

9. **Dynamic Driver Registry Search Bar**:
   - Added an interactive search entry field at the top of the **Driver Registry** panel ([driver_manager.py](file:///C:/Users/pintoan/.gemini/antigravity/scratch/torque_tester/views/driver_manager.py)).
   - Triggers dynamic filtering as the operator/supervisor types, querying on Driver ID, Brand, Model, Type, or Workbench.

10. **Database Connection Configuration (Local SQLite / Online SQL Server)**:
    - Added a "Database Location" configuration panel in the Settings right tabview.
    - Enables administrators to switch connection types, customize local SQLite paths, or specify an online Microsoft SQL Server connection string (translates standard ADO.NET syntax parameters like `Data Source` and `Initial Catalog` directly into valid pyodbc connections with automatic T-SQL syntax translations).

11. **Custom Tester Model & Serial Reader Pattern**:
    - Select `"Custom…"` in settings to reveal custom settings: Model name, min/max torque limits, and a custom serial regex reader pattern (e.g. `([+-]?\d+\.\d+)\s*Nm`).
    - The serial parser automatically reads newline-terminated ASCII values matching the regex.
    - Resolves custom maximum torque limits to scale the live TorqueGauge indicator on the Test Runner.

12. **Multi-Sensor Support (Tester C+)**:
    - Added dynamic sensor slots based on the `tester_count` setting.
    - Tab bar expands dynamically with a `+` tab at the end (for Admins). Clicking it adds a new Tester tab and initializes serial configurations.
    - Default Tester dropdown selector in Test Setup automatically lists all available testers (Tester A, Tester B, Tester C...).

13. **Search in Procedure Templates**:
    - Added an interactive search entry field at the top of the **Procedure Templates** registry table.
    - Dynamically filters the list by name, test type, and default tester assignment.

14. **Clone Driver & Clone Test Template Options**:
    - Added "Clone" action buttons to both the Driver Registry and Procedure Templates tables.
    - Pre-populates all registration fields with copy details but clears the unique primary identifiers (Driver ID / Template Name) and updates form titles to prompt for new names.

15. **Tester Deletion Option (Tester C+)**:
    - Tester slots above the core A & B configuration can be safely deleted.
    - A "Delete Tester [Letter]" button is dynamically shown on the last tester's configuration tab.
    - Clicking it deletes its configuration section in `hardware.ini`, decrements the active `tester_count`, and triggers a hot-reconnect and settings refresh.

16. **Local settings separation via `hardware.ini` file**:
    - Removed hardware configuration storage from SQLite/SQL Server database schema.
    - Introduced a dedicated machine-local `hardware.ini` INI configuration file.
    - Configured automatic transparent settings migration on first launch: reads existing keys from `app_settings` database table, populates them to `hardware.ini` split into clean sections (`[general]`, `[tester_a]`, `[tester_b]`, etc.), and drops the old table to clean up database schemas.

17. **Compiled Release Executable (One-File Mode)**:
    - Built a single-file executable at `dist/TorqueTester.exe` using PyInstaller.
    - Unpacks all runtime dependencies, customtkinter themes/assets, and core python dynamic libraries into a secure temporary runtime folder (`_MEIxxxxxx`) automatically on Windows startup, bypassing Visual C++ search path limits and resolved DLL load errors.


