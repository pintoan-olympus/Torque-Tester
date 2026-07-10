import os
import customtkinter as ctk
from typing import Type
import config
from utils.logger import get_logger, log_action
from database.db_manager import DatabaseManager
from auth.user_manager import UserManager
from sensor.sensor_interface import TorqueSensorInterface
from sensor.simulator import TorqueSensorSimulator
from sensor.serial_comm import TorqueSensorSerial
from hardware_config import HardwareConfig
import i18n

logger = get_logger()

class TorqueTesterApp(ctk.CTk):
    @property
    def sensor(self) -> TorqueSensorInterface:
        if self.selected_test_def:
            tester_id = getattr(self.selected_test_def, 'default_tester_id', 'A')
            idx = ord(tester_id.upper()) - 65
            if 0 <= idx < len(self.sensors):
                return self.sensors[idx]
        return self.sensors[0] if len(self.sensors) > 0 else None

    @property
    def sensor_a(self) -> TorqueSensorInterface:
        return self.sensors[0] if len(self.sensors) > 0 else None

    @sensor_a.setter
    def sensor_a(self, val):
        while len(self.sensors) < 1:
            self.sensors.append(None)
        self.sensors[0] = val

    @property
    def sensor_b(self) -> TorqueSensorInterface:
        return self.sensors[1] if len(self.sensors) > 1 else None

    @sensor_b.setter
    def sensor_b(self, val):
        while len(self.sensors) < 2:
            self.sensors.append(None)
        self.sensors[1] = val

    def __init__(self, db_manager: DatabaseManager, user_manager: UserManager):
        super().__init__()
        
        self.db = db_manager
        self.user_manager = user_manager
        self.hw_config = HardwareConfig()
        saved_lang = self.hw_config.get_setting("language", "en")
        i18n.set_language(saved_lang)
        self.sensors: list[TorqueSensorInterface] = []
        self.selected_workbench = ""
        self.selected_driver = None
        self.selected_test_def = None
        self.selected_battery = None
        self.battery_items = []
        self.current_battery_step = 0
        self.battery_session_id = None
        
        # Configure main window
        self.title(f"{config.APP_NAME} - v{config.VERSION}")
        self.geometry("1100x700")
        self.minimum_size = (950, 600)
        self.minsize(*self.minimum_size)
        
        # Configure layout (2 columns: navigation, content; 2 rows: content, statusbar)
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=1) # Main Content
        self.grid_rowconfigure(0, weight=1)    # Content Row
        self.grid_rowconfigure(1, weight=0)    # Status Bar
        
        # Main containers
        self.sidebar_frame = None
        self.main_content_frame = None
        self.statusbar_frame = None
        self.current_view = None
        
        # Initialize sensor connection based on settings
        self.reconnect_sensor()
        
        # Start with Login Screen
        self.show_login()
        
        # Handle close window event
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Periodically monitor sensor status
        self.update_sensor_status_bar()

    def show_login(self):
        """Display login frame and hide navigation sidebar."""
        # Cleanup any existing frames
        if self.sidebar_frame:
            self.sidebar_frame.destroy()
            self.sidebar_frame = None
        if self.statusbar_frame:
            self.statusbar_frame.destroy()
            self.statusbar_frame = None
        if self.main_content_frame:
            self.main_content_frame.destroy()
            self.main_content_frame = None
            
        from auth.login_view import LoginView
        
        # Main container for login centered
        self.grid_columnconfigure(0, weight=1)
        self.current_view = LoginView(master=self, app=self)
        self.current_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    def on_login_success(self):
        """Called by LoginView when authentication succeeds."""
        self.current_view.destroy()
        
        # Re-configure grid for Sidebar layout
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        
        # Build layout elements
        self.build_sidebar()
        self.build_statusbar()
        self.build_main_content_area()
        
        # Navigate to Dashboard
        from views.dashboard import DashboardView
        self.show_view(DashboardView)

    def build_sidebar(self):
        """Build sidebar navigation panel."""
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        # Logo / Title
        logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="TORQUE TESTER", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        logo_label.pack(padx=20, pady=(20, 30))
        
        # User details card
        user = self.user_manager.current_user
        role_name = config.ACCESS_LEVEL_NAMES.get(user.access_level, "Operator")
        translated_role = i18n.t(f"role.{role_name.lower()}")
        if translated_role == f"role.{role_name.lower()}":
            translated_role = role_name
            
        user_card = ctk.CTkFrame(self.sidebar_frame, fg_color="gray15")
        user_card.pack(fill="x", padx=10, pady=(0, 20))
        
        user_name_lbl = ctk.CTkLabel(user_card, text=user.full_name, font=ctk.CTkFont(size=12, weight="bold"))
        user_name_lbl.pack(pady=(5, 0))
        
        user_role_lbl = ctk.CTkLabel(user_card, text=translated_role, text_color="gray60", font=ctk.CTkFont(size=10))
        user_role_lbl.pack(pady=(0, 5))
        
        # Navigation Buttons definitions: (Label, ViewClass, RequiredAccess)
        from views.dashboard import DashboardView
        from views.test_runner import TestRunnerView
        from views.test_history import TestHistoryView
        from views.driver_manager import DriverManagerView
        from views.test_setup import TestSetupView
        from views.battery_setup import BatterySetupView
        from views.user_admin import UserAdminView
        from views.settings_view import SettingsView
 
        nav_items = [
            ("nav.dashboard", DashboardView, config.ACCESS_OPERATOR),
            ("nav.test_runner", TestRunnerView, config.ACCESS_OPERATOR),
            ("nav.history", TestHistoryView, config.ACCESS_OPERATOR),
            ("nav.drivers", DriverManagerView, config.ACCESS_SUPERVISOR),
            ("nav.test_setup", TestSetupView, config.ACCESS_SUPERVISOR),
            ("nav.batteries", BatterySetupView, config.ACCESS_ADMIN),
            ("nav.user_admin", UserAdminView, config.ACCESS_ADMIN),
            ("nav.settings", SettingsView, config.ACCESS_OPERATOR),  # Everyone can view settings, admin edits
        ]
        
        self.nav_buttons = {}
        for label_key, view_class, req_access in nav_items:
            if self.user_manager.has_access(req_access):
                btn = ctk.CTkButton(
                    self.sidebar_frame,
                    text=i18n.t(label_key),
                    anchor="w",
                    fg_color="transparent",
                    text_color="gray80",
                    hover_color="gray25",
                    command=lambda vc=view_class: self.show_view(vc)
                )
                btn.pack(fill="x", padx=10, pady=2)
                self.nav_buttons[view_class] = btn
                
        # Logout button at bottom
        logout_btn = ctk.CTkButton(
            self.sidebar_frame,
            text=i18n.t("nav.logout"),
            anchor="w",
            fg_color="transparent",
            text_color="red2",
            hover_color="gray25",
            command=self.logout
        )
        logout_btn.pack(side="bottom", fill="x", padx=10, pady=15)

    def build_statusbar(self):
        """Build status bar at bottom of application."""
        self.statusbar_frame = ctk.CTkFrame(self, height=25, corner_radius=0, fg_color="gray12")
        self.statusbar_frame.grid(row=1, column=1, sticky="ew")
        
        self.status_lbl = ctk.CTkLabel(
            self.statusbar_frame, 
            text="Sensor: Checking...", 
            font=ctk.CTkFont(size=11), 
            padx=10
        )
        self.status_lbl.pack(side="left")
        
        self.workbench_lbl = ctk.CTkLabel(
            self.statusbar_frame, 
            text=f"Workbench: {self.selected_workbench or 'None'}", 
            font=ctk.CTkFont(size=11), 
            padx=10
        )
        self.workbench_lbl.pack(side="right")

    def build_main_content_area(self):
        """Build holding frame for main screen views."""
        self.main_content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_content_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=1)

    def show_view(self, view_class: Type[ctk.CTkFrame], **kwargs):
        """Switch current view inside main content frame."""
        if not self.main_content_frame:
            return
            
        # Clean current view
        if self.current_view:
            self.current_view.destroy()
            
        # Update navigation highlights
        for vc, btn in self.nav_buttons.items():
            if vc == view_class:
                btn.configure(fg_color="gray30", text_color="white")
            else:
                btn.configure(fg_color="transparent", text_color="gray80")
                
        # Instantiate and display new view
        self.current_view = view_class(master=self.main_content_frame, app=self, **kwargs)
        self.current_view.grid(row=0, column=0, sticky="nsew")
        logger.debug(f"Navigated to view: {view_class.__name__}")

    def logout(self):
        """Handle logout and clean up state."""
        self.user_manager.logout()
        self.selected_workbench = ""
        self.selected_driver = None
        self.selected_test_def = None
        self.show_login()

    def update_workbench(self, workbench_name):
        self.selected_workbench = workbench_name
        if self.statusbar_frame:
            self.workbench_lbl.configure(text=f"Workbench: {workbench_name or 'None'}")

    def reconnect_sensor(self):
        """Reconnect all configured sensors using hardware config settings."""
        tester_count = self.hw_config.get_setting("tester_count", 2)
        while len(self.sensors) < tester_count:
            self.sensors.append(None)
        for i in range(tester_count):
            self.reconnect_sensor_by_idx(i)

    def reconnect_sensor_by_idx(self, idx: int):
        while len(self.sensors) <= idx:
            self.sensors.append(None)
            
        if self.sensors[idx]:
            try:
                self.sensors[idx].disconnect()
            except Exception:
                pass
            self.sensors[idx] = None

        suffix = "" if idx == 0 else (f"_b" if idx == 1 else f"_{chr(97 + idx)}")
        sim_mode = self.hw_config.get_setting(f"simulator_mode{suffix}", True)
        tester_model = self.hw_config.get_setting(f"tester_model{suffix}", "ng-TTS50-xu")

        if sim_mode:
            logger.info(f"Initializing Tester {chr(65 + idx)} in SIMULATOR mode")
            self.sensors[idx] = TorqueSensorSimulator()
        else:
            port = self.hw_config.get_setting(f"port{suffix}", f"COM{idx+1}")
            baud = self.hw_config.get_setting(f"baudrate{suffix}", 9600)
            bytesize = self.hw_config.get_setting(f"bytesize{suffix}", 8)
            parity = self.hw_config.get_setting(f"parity{suffix}", "N")
            stopbits = self.hw_config.get_setting(f"stopbits{suffix}", 1)
            timeout = self.hw_config.get_setting(f"timeout{suffix}", 1.0)
            
            val_pattern = None
            if tester_model == "Custom…":
                val_pattern = self.hw_config.get_setting(f"custom_serial_pattern{suffix}", r"([+-]?\d+\.\d+)\s*Nm")

            logger.info(f"Initializing Tester {chr(65 + idx)} in SERIAL mode on {port}")
            self.sensors[idx] = TorqueSensorSerial(
                port=port,
                baudrate=baud,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout,
                value_pattern=val_pattern
            )
        try:
            self.sensors[idx].connect()
        except Exception as e:
            logger.error(f"Error connecting Tester {chr(65 + idx)}: {e}")

    def reconnect_sensor_a(self):
        self.reconnect_sensor_by_idx(0)

    def reconnect_sensor_b(self):
        self.reconnect_sensor_by_idx(1)

    def update_sensor_status_bar(self):
        """Periodic status bar updates."""
        if self.statusbar_frame:
            msg = []
            tester_count = self.hw_config.get_setting("tester_count", 2)
            is_ok = False
            for idx in range(tester_count):
                letter = chr(65 + idx)
                if idx < len(self.sensors) and self.sensors[idx] and self.sensors[idx].is_connected():
                    info = self.sensors[idx].get_status_info()
                    msg.append(f"{letter}: {info.get('port', 'Sim')}")
                    is_ok = True
                else:
                    msg.append(f"{letter}: Offline")
                
            text = " | ".join(msg)
            self.status_lbl.configure(
                text=f"Sensors: {text}",
                text_color="green" if is_ok else "red"
            )
                
        # Run check every 2 seconds
        self.after(2000, self.update_sensor_status_bar)

    def on_close(self):
        """Perform cleanup actions on window closing."""
        logger.info("Closing application. Cleaning up resources...")
        for s in self.sensors:
            if s:
                try:
                    s.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting sensor during close: {e}")
        self.destroy()
