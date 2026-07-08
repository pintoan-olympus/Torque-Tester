import sys
import os
import urllib.parse
import customtkinter as ctk
import config
from utils.logger import get_logger
from database.db_manager import DatabaseManager
from auth.user_manager import UserManager
from app import TorqueTesterApp

logger = get_logger()

# Enable Per-Monitor DPI awareness on Windows for crisp rendering on high-DPI screens
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass  # Non-fatal; silently ignore on older Windows versions

def main():
    logger.info("=========================================")
    logger.info(f"Starting {config.APP_NAME} v{config.VERSION}")
    logger.info("=========================================")
    
    # Set customtkinter appearance
    ctk.set_appearance_mode("dark")  # Modes: "System", "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue", "green", "dark-blue"
    
    try:
        # Initialize Database
        db_manager = DatabaseManager()
        
        # Initialize User Manager (Seeds default admin if db empty)
        user_manager = UserManager(db_manager)
        
        # Launch UI
        app = TorqueTesterApp(db_manager, user_manager)
        app.mainloop()
        
    except Exception as e:
        logger.critical(f"Unhandled exception during app startup: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
