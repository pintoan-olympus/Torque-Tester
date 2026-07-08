import sys
import os

# Add root folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Verifying imports for Torque Tester modules...")

try:
    import config
    print("[OK] config imported")
    import database.models
    print("[OK] database.models imported")
    import database.db_manager
    print("[OK] database.db_manager imported")
    import auth.user_manager
    print("[OK] auth.user_manager imported")
    import utils.logger
    print("[OK] utils.logger imported")
    import utils.helpers
    print("[OK] utils.helpers imported")
    import sensor.sensor_interface
    print("[OK] sensor.sensor_interface imported")
    import sensor.simulator
    print("[OK] sensor.simulator imported")
    import sensor.serial_comm
    print("[OK] sensor.serial_comm imported")
    import auth.login_view
    print("[OK] auth.login_view imported")
    import views.components
    print("[OK] views.components imported")
    import views.dashboard
    print("[OK] views.dashboard imported")
    import views.test_runner
    print("[OK] views.test_runner imported")
    import views.test_history
    print("[OK] views.test_history imported")
    import views.driver_manager
    print("[OK] views.driver_manager imported")
    import views.test_setup
    print("[OK] views.test_setup imported")
    import views.user_admin
    print("[OK] views.user_admin imported")
    import views.settings_view
    print("[OK] views.settings_view imported")
    import app
    print("[OK] app imported")
    
    print("\nSUCCESS: All modules imported successfully without errors!")
    sys.exit(0)
except Exception as e:
    print(f"\nFAILURE: Import check failed with error: {e}")
    sys.exit(1)
