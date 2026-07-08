import sys
import os
import customtkinter as ctk

# Add root folder to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from auth.user_manager import UserManager
from app import TorqueTesterApp
from views.settings_view import SettingsView

print("Starting settings view crash test...")

try:
    # Set customtkinter appearance
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Initialize DB and User Manager
    db_manager = DatabaseManager()
    user_manager = UserManager(db_manager)
    
    # Login as admin
    user_manager.login("admin", "admin")
    
    # Instantiate App (without starting mainloop)
    app = TorqueTesterApp(db_manager, user_manager)
    
    # Force navigation to SettingsView
    print("Navigating to SettingsView...")
    app.on_login_success()  # Creates sidebar & main_content_frame
    app.show_view(SettingsView)
    
    # Update Tkinter tasks to trigger all initialization and first callbacks
    print("Running Tkinter update...")
    app.update_idletasks()
    app.update()
    
    print("SUCCESS: SettingsView loaded and updated without crash!")
    app.destroy()
    sys.exit(0)
    
except Exception as e:
    import traceback
    print("\nCRITICAL: SettingsView crash detected!")
    traceback.print_exc()
    sys.exit(1)
