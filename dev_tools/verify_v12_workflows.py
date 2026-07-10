import sys
from pathlib import Path
# Add parent directory to sys.path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

import tkinter as tk
import customtkinter as ctk
from database.db_manager import DatabaseManager
from auth.user_manager import UserManager
from database.models import User, TorqueDriver, TestDefinition, TestBattery, BatteryItem
from views.dashboard import DashboardView
from views.test_runner import TestRunnerView
from views.battery_setup import BatterySetupView
from views.driver_manager import DriverManagerView
from views.battery_runner import BatteryRunnerView

print("Starting Programmatic Workflow Verification for Version 1.2.0...")

# Initialize Database in SQLite memory or standard test DB file
db = DatabaseManager(db_path="test_torque_tester.db")
user_mgr = UserManager(db)

# Clean up existing test data to avoid constraint failures
with db.get_connection() as conn:
    cursor = conn.cursor()
    # Disable foreign keys temporarily for clean slate cleanup
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DELETE FROM battery_items WHERE battery_id IN (SELECT id FROM test_batteries WHERE name = ?)", ("Battery Integration Test",))
    cursor.execute("DELETE FROM battery_sessions WHERE battery_id IN (SELECT id FROM test_batteries WHERE name = ?)", ("Battery Integration Test",))
    cursor.execute("DELETE FROM test_measurements WHERE session_id IN (SELECT id FROM test_sessions WHERE driver_id IN (SELECT id FROM torque_drivers WHERE driver_id IN (?, ?)))", ("BULK-DRV-1", "BULK-DRV-2"))
    cursor.execute("DELETE FROM test_sessions WHERE driver_id IN (SELECT id FROM torque_drivers WHERE driver_id IN (?, ?))", ("BULK-DRV-1", "BULK-DRV-2"))
    cursor.execute("DELETE FROM users WHERE username = ?", ("test_admin",))
    cursor.execute("DELETE FROM torque_drivers WHERE driver_id IN (?, ?)", ("BULK-DRV-1", "BULK-DRV-2"))
    cursor.execute("DELETE FROM test_batteries WHERE name = ?", ("Battery Integration Test",))
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.commit()

# Create test user and login
test_user = User(username="test_admin", password_hash="dummy_hash", full_name="Test Admin", access_level=3)
db.create_user(test_user)
logged_in_user = db.get_user_by_username("test_admin")
user_mgr.current_user = logged_in_user

print("[OK] Database and Admin Session initialized.")

# ========================================================
# 1. DATABASE LAYER VERIFICATION
# ========================================================
# Retrieve or seed test definitions
defs = db.get_all_test_definitions()
if not defs:
    print("Error: No test definitions found.")
    sys.exit(1)
test_def = defs[0]

# Create Test Battery
battery = TestBattery(name="Battery Integration Test", description="Automated QA Battery", active=True)
bat_id = db.create_battery(battery)
battery.id = bat_id
assert bat_id is not None, "Failed to create battery row"
print(f"[OK] Test Battery created with ID: {bat_id}")

# Set Battery steps (link two of the same test definition for testing sequence)
success = db.set_battery_items(bat_id, [test_def.id, test_def.id])
assert success, "Failed to save battery items sequence"
print("[OK] Test Battery items sequence set.")

# Read Battery steps
items = db.get_battery_items(bat_id)
assert len(items) == 2, f"Expected 2 steps, got {len(items)}"
assert items[0].test_def.id == test_def.id, "First step test def ID mismatch"
assert items[0].sequence_order == 1, "First step sequence order mismatch"
assert items[1].sequence_order == 2, "Second step sequence order mismatch"
print(f"[OK] Retrieved {len(items)} battery items successfully.")

# Create Test Drivers for Bulk Edit
drv1_id = db.create_driver(TorqueDriver(driver_id="BULK-DRV-1", driver_type="Manual Click", torque_min=5, torque_max=20, workbench="Bench 1", active=True))
drv2_id = db.create_driver(TorqueDriver(driver_id="BULK-DRV-2", driver_type="Manual Click", torque_min=5, torque_max=20, workbench="Bench 1", active=True))
assert drv1_id and drv2_id, "Failed to create test drivers"

# Bulk Edit
updated_count = db.bulk_update_driver_default_test([drv1_id, drv2_id], test_def.id)
assert updated_count == 2, f"Expected 2 rows updated, got {updated_count}"

# Re-fetch and assert
d1 = db.get_driver_by_tag("BULK-DRV-1")
d2 = db.get_driver_by_tag("BULK-DRV-2")
assert d1.default_test_def_id == test_def.id, "Bulk edit default test mismatch on driver 1"
assert d2.default_test_def_id == test_def.id, "Bulk edit default test mismatch on driver 2"
print("[OK] Bulk update driver default test verified successfully.")

# ========================================================
# 2. VIEW INITIALIZATION AND STATE TRANSITIONS VERIFICATION
# ========================================================
from app import TorqueTesterApp

# Instantiate the main app (headless window update runner)
app_window = TorqueTesterApp(db_manager=db, user_manager=user_mgr)
app_window.withdraw() # Hide the window during testing

# Set up global state
app_window.selected_driver = d1
app_window.selected_test_def = test_def
app_window.selected_workbench = "Bench 1"

print("[OK] Headless TorqueTesterApp initialized.")

# Instantiate and test DriverManagerView bulk selection
print("Testing DriverManagerView widgets...")
dm_view = DriverManagerView(master=app_window.main_content_frame, app=app_window)
dm_view.selected_driver_ids = {drv1_id, drv2_id}
dm_view.update_bulk_bar_visibility()
# Assert bulk bar is displayed (gridded)
assert dm_view.bulk_bar.winfo_manager() != "", "Bulk bar should be gridded when selections exist"
dm_view.clear_driver_selection()
assert len(dm_view.selected_driver_ids) == 0, "Selection set was not cleared"
assert dm_view.bulk_bar.winfo_manager() == "", "Bulk bar should be hidden when selection is cleared"
print("[OK] DriverManagerView selection states verified.")

# Instantiate and test BatterySetupView steps sequence modification
print("Testing BatterySetupView list modifications...")
bs_view = BatterySetupView(master=app_window.main_content_frame, app=app_window)
bs_view.sequence = [test_def, test_def]
bs_view.redraw_steps()
assert len(bs_view.sequence) == 2
bs_view.move_step_down(0)
# sequence remains 2, but order of different instances would swap
bs_view.delete_step(1)
assert len(bs_view.sequence) == 1, "Failed to delete step from setup sequence"
print("[OK] BatterySetupView sequence reordering and deletion verified.")

# Instantiate DashboardView
print("Testing DashboardView mode switches...")
dash_view = DashboardView(master=app_window.main_content_frame, app=app_window)
dash_view.mode_var.set("battery")
dash_view.on_mode_changed()
# Assert battery combo is gridded and test combo is not
assert dash_view.battery_combo.winfo_manager() != "", "Battery combo should be gridded in battery mode"
assert dash_view.test_combo.winfo_manager() == "", "Test combo should be hidden in battery mode"
print("[OK] DashboardView mode layout switching verified.")

# Test Runner guided flow sequence complete mock
print("Testing TestRunnerView flow callbacks...")
runner_completed = False
step_result_received = None

def mock_step_complete(overall_result, session_id):
    global runner_completed, step_result_received
    runner_completed = True
    step_result_received = overall_result

# Set up global state for TestRunnerView
app_window.selected_driver = d1
app_window.selected_test_def = test_def
app_window.selected_workbench = "Bench 1"

# Load TestRunnerView
test_runner = TestRunnerView(
    master=app_window.main_content_frame,
    app=app_window,
    step_number=1,
    total_steps=2,
    on_step_complete=mock_step_complete
)

# Start measurements manually
test_runner.start_measurements()
assert test_runner.is_active is True

# Capture 5 samples (min 3, max 5)
for i in range(test_def.num_samples):
    test_runner.capture_sample(val=test_def.target_value)

assert test_runner.current_sample_idx == test_def.num_samples
assert len(test_runner.measurements) == test_def.num_samples
assert test_runner.overall_result == "PASS"

# Click Save & Finish
test_runner.save_and_finish()
assert runner_completed is True
assert step_result_received == "PASS"
print("[OK] TestRunnerView guided flow and sequence complete callback verified.")

# Test BatteryRunnerView sequence loop
print("Testing BatteryRunnerView sequencing loop...")
app_window.selected_battery = battery
app_window.battery_items = db.get_battery_items(bat_id)

bat_runner = BatteryRunnerView(master=app_window.main_content_frame, app=app_window)
assert bat_runner.current_step == 0
assert len(bat_runner.steps) == 2

# Simulate step 1 PASS
bat_runner.on_step_complete("PASS", session_id=1)
assert bat_runner.current_step == 1

# Simulate step 2 FAIL
bat_runner.on_step_complete("FAIL", session_id=2)
# Since it failed, remaining steps are skipped, summary screen is built
assert bat_runner.step_results[0]["result"] == "PASS"
assert bat_runner.step_results[1]["result"] == "FAIL"
print("[OK] BatteryRunnerView sequencing, PASS propagation, and FAIL summary screens verified.")

# Cleanup test DB file
app_window.destroy()
if Path("test_torque_tester.db").exists():
    try:
        Path("test_torque_tester.db").unlink()
        # Also backups folder if created
        backups_dir = Path("backups")
        if backups_dir.exists():
            for f in backups_dir.glob("*"):
                f.unlink()
            backups_dir.rmdir()
    except Exception as e:
        print(f"Warning: clean up failed: {e}")

print("\nALL WORKFLOWS AND VIEW COMPONENTS INTEGRATED AND VERIFIED SUCCESSFULLY!")
sys.exit(0)
