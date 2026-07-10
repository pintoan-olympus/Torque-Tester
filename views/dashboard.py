import customtkinter as ctk
from datetime import datetime
from utils.logger import get_logger
from views.test_runner import TestRunnerView

logger = get_logger()

class DashboardView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._debounce_after_id = None  # Tracks pending debounce call
        
        # Grid layout (2 columns: left for setup/actions, right for info/summary)
        self.grid_columnconfigure(0, weight=3, uniform="cols")
        self.grid_columnconfigure(1, weight=2, uniform="cols")
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT FRAME: Session Setup ---
        self.setup_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.setup_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.setup_frame.grid_columnconfigure(0, weight=1)
        
        # Section Title
        lbl = ctk.CTkLabel(self.setup_frame, text="TEST SESSION INITIALIZATION", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(pady=20, padx=20, anchor="w")
        
        # 1. Select Driver
        drivers = self.app.db.get_all_drivers()
        d_lbl = ctk.CTkLabel(self.setup_frame, text="1. Driver ID (Scan or Select)", font=ctk.CTkFont(size=12, weight="bold"))
        d_lbl.pack(pady=(10, 2), padx=20, anchor="w")
        
        self.driver_ids = [d.driver_id for d in drivers if d.active]
        self.driver_id_var = ctk.StringVar()
        self.driver_combo = ctk.CTkComboBox(
            self.setup_frame, 
            values=self.driver_ids, 
            variable=self.driver_id_var, 
            width=350,
            command=self.on_driver_selected
        )
        self.driver_combo.pack(pady=(0, 15), padx=20, anchor="w")
        self.driver_id_var.trace_add("write", self._on_driver_id_changed)

        # 2. Select Workbench
        w_lbl = ctk.CTkLabel(self.setup_frame, text="2. Workbench Name / ID", font=ctk.CTkFont(size=12, weight="bold"))
        w_lbl.pack(pady=(10, 2), padx=20, anchor="w")
        
        workbenches = sorted(list(set(d.workbench for d in drivers if d.workbench)))
        if not workbenches:
            workbenches = ["Workbench A", "Workbench B", "Workbench C"]
            
        self.workbench_var = ctk.StringVar(value=self.app.selected_workbench)
        self.workbench_combo = ctk.CTkComboBox(
            self.setup_frame, 
            values=workbenches, 
            variable=self.workbench_var, 
            width=350,
            command=self.on_workbench_changed
        )
        self.workbench_combo.pack(pady=(0, 15), padx=20, anchor="w")
        
        # 3. Selection Mode (Single Test vs Battery Test)
        m_lbl = ctk.CTkLabel(self.setup_frame, text="3. Selection Mode", font=ctk.CTkFont(size=12, weight="bold"))
        m_lbl.pack(pady=(10, 2), padx=20, anchor="w")

        self.mode_var = ctk.StringVar(value="single")
        self.mode_frame = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        self.mode_frame.pack(pady=(0, 10), padx=20, fill="x", anchor="w")

        self.radio_single = ctk.CTkRadioButton(
            self.mode_frame,
            text="Single Test",
            variable=self.mode_var,
            value="single",
            command=self.on_mode_changed
        )
        self.radio_single.pack(side="left", padx=(0, 20))

        self.radio_battery = ctk.CTkRadioButton(
            self.mode_frame,
            text="Battery Test",
            variable=self.mode_var,
            value="battery",
            command=self.on_mode_changed
        )
        self.radio_battery.pack(side="left")

        # 4. Select Test Procedure or Battery
        self.procedure_lbl = ctk.CTkLabel(self.setup_frame, text="4. Select Test Template", font=ctk.CTkFont(size=12, weight="bold"))
        self.procedure_lbl.pack(pady=(10, 2), padx=20, anchor="w")
        
        # Load Test Definitions
        test_defs = self.app.db.get_all_test_definitions()
        self.test_names = [td.name for td in test_defs if td.active]
        self.test_def_map = {td.name: td for td in test_defs if td.active}
        
        self.test_name_var = ctk.StringVar()
        self.test_combo = ctk.CTkComboBox(
            self.setup_frame, 
            values=self.test_names, 
            variable=self.test_name_var, 
            width=350,
            state="disabled" if not self.test_names else "normal",
            command=self.on_test_selected
        )
        self.test_combo.pack(pady=(0, 20), padx=20, anchor="w")

        # Load Batteries
        batteries = self.app.db.get_all_batteries()
        self.battery_names = [b.name for b in batteries if b.active]
        self.battery_map = {b.name: b for b in batteries if b.active}

        self.battery_name_var = ctk.StringVar()
        self.battery_combo = ctk.CTkComboBox(
            self.setup_frame,
            values=self.battery_names,
            variable=self.battery_name_var,
            width=350,
            state="disabled" if not self.battery_names else "normal",
            command=self.on_battery_selected
        )
        # Will be packed dynamically inside on_mode_changed()
        
        # Start button
        self.start_btn = ctk.CTkButton(
            self.setup_frame, 
            text="Start Test Session", 
            height=40, 
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self.start_session
        )
        self.start_btn.pack(pady=20, padx=20, fill="x")

        # --- RIGHT FRAME: Driver Details & Cal Status ---
        self.details_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.details_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.details_frame.grid_columnconfigure(0, weight=1)
        
        # Section Title
        lbl2 = ctk.CTkLabel(self.details_frame, text="EQUIPMENT PROFILE", font=ctk.CTkFont(size=16, weight="bold"))
        lbl2.pack(pady=20, padx=20, anchor="w")
        
        # Card body with dynamic text
        self.info_card = ctk.CTkFrame(self.details_frame, fg_color="gray12", corner_radius=6)
        self.info_card.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.details_lbl = ctk.CTkLabel(
            self.info_card, 
            text="Scan or select a Torque Driver ID to view details and calibration records.",
            font=ctk.CTkFont(size=12),
            text_color="gray60",
            wraplength=280,
            justify="left"
        )
        self.details_lbl.pack(padx=20, pady=40)

        # Pre-select fields if already stored in app state
        if self.app.selected_driver:
            self.driver_id_var.set(self.app.selected_driver.driver_id)
            self.on_driver_selected(self.app.selected_driver.driver_id)
        if self.app.selected_battery:
            self.mode_var.set("battery")
            self.on_mode_changed()
            self.battery_name_var.set(self.app.selected_battery.name)
            self.on_battery_selected(self.app.selected_battery.name)
        elif self.app.selected_test_def:
            self.mode_var.set("single")
            self.on_mode_changed()
            self.test_name_var.set(self.app.selected_test_def.name)
            self.on_test_selected(self.app.selected_test_def.name)
        else:
            self.on_mode_changed()

        # Lock controls for Operator access level (Access level <= 1)
        if self.app.user_manager.current_user.access_level <= 1:
            self.radio_single.configure(state="disabled")
            self.radio_battery.configure(state="disabled")
            self.test_combo.configure(state="disabled")
            self.battery_combo.configure(state="disabled")

        # USB HID Barcode scanner buffer setup
        self._scan_buffer = []
        self._last_scan_time = 0.0
        
        # Bind global keypress event
        try:
            self.winfo_toplevel().bind("<Key>", self.on_global_key)
        except Exception as e:
            logger.error(f"DashboardView: Failed to bind global keys: {e}")

    def on_workbench_changed(self, choice):
        self.app.update_workbench(choice.strip())
        self.validate_inputs()

    def _on_driver_id_changed(self, *args):
        """Debounced trace handler: waits 300ms after last keystroke before querying the DB."""
        if self._debounce_after_id:
            self.after_cancel(self._debounce_after_id)
        self._debounce_after_id = self.after(300, self.check_driver_exists)

    def check_driver_exists(self):
        val = self.driver_id_var.get().strip()
        driver = self.app.db.get_driver_by_tag(val)
        if driver:
            self.on_driver_selected(val)
        else:
            self.details_lbl.configure(
                text="Driver ID not recognized or inactive.",
                text_color="red"
            )
            self.start_btn.configure(state="disabled")

    def on_driver_selected(self, driver_id):
        driver_id = driver_id.strip()
        driver = self.app.db.get_driver_by_tag(driver_id)
        if not driver:
            return
            
        self.app.selected_driver = driver
        
        # Format dates
        cal_date = driver.calibration_date or "None"
        due_date = driver.calibration_due or "None"
        
        # Check if calibration is overdue
        is_overdue = False
        cal_status_text = "CALIBRATION OK"
        status_color = "green"
        if driver.calibration_due:
            try:
                due = datetime.strptime(driver.calibration_due, "%Y-%m-%d").date()
                if due < datetime.now().date():
                    is_overdue = True
                    cal_status_text = "CALIBRATION OVERDUE!"
                    status_color = "red"
            except ValueError:
                pass
                
        # Get last test recorded
        last_test_str = "None"
        history = self.app.db.get_test_history(driver_id_str=driver.driver_id)
        exact_history = [h for h in history if h.get("driver_id_str") == driver.driver_id]
        if exact_history:
            last_run = exact_history[0]
            test_date = last_run.get("completed_at") or last_run.get("started_at") or "Unknown"
            if test_date and test_date != "Unknown":
                try:
                    clean_date = test_date.replace("T", " ").split(".")[0]
                    dt = datetime.strptime(clean_date, "%Y-%m-%d %H:%M:%S")
                    date_formatted = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_formatted = test_date
            else:
                date_formatted = "Unknown"
            result = last_run.get("overall_result", "N/A")
            last_test_str = f"{date_formatted} ({result})"

        # Update Profile Details Card
        profile_text = (
            f"ID: {driver.driver_id}\n"
            f"Type: {driver.driver_type}\n"
            f"Brand: {driver.brand or 'N/A'}\n"
            f"Model: {driver.model or 'N/A'}\n"
            f"Range: {driver.torque_min} - {driver.torque_max} cNm\n"
            f"Default Workbench: {driver.workbench}\n\n"
            f"Last Cal Date: {cal_date}\n"
            f"Next Cal Due: {due_date}\n\n"
            f"Cal Status: {cal_status_text}\n"
            f"Last Test: {last_test_str}"
        )
        
        self.details_lbl.configure(
            text=profile_text,
            text_color=status_color if is_overdue else "white",
            justify="left",
            anchor="w",
            wraplength=280
        )
        
        # Auto fill workbench if empty
        if not self.workbench_var.get().strip() and driver.workbench:
            self.workbench_var.set(driver.workbench)
            self.app.update_workbench(driver.workbench)

        # Auto select default test template or battery
        has_default = False
        if driver.default_test_def_id:
            test_defs = self.app.db.get_all_test_definitions()
            default_test = next((td for td in test_defs if td.id == driver.default_test_def_id), None)
            if default_test and default_test.active:
                self.mode_var.set("single")
                self.on_mode_changed()
                self.test_name_var.set(default_test.name)
                self.on_test_selected(default_test.name)
                has_default = True
        elif getattr(driver, 'default_battery_id', None):
            batteries = self.app.db.get_all_batteries()
            default_bat = next((b for b in batteries if b.id == driver.default_battery_id), None)
            if default_bat and default_bat.active:
                self.mode_var.set("battery")
                self.on_mode_changed()
                self.battery_name_var.set(default_bat.name)
                self.on_battery_selected(default_bat.name)
                has_default = True

        if not has_default:
            self.mode_var.set("single")
            self.on_mode_changed()
            self.test_name_var.set("")
            self.app.selected_test_def = None
            self.app.selected_battery = None
            self.app.battery_items = []

        # Lock/unlock controls dynamically based on Operator access level
        if self.app.user_manager.current_user.access_level <= 1:
            self.radio_single.configure(state="disabled")
            self.radio_battery.configure(state="disabled")
            self.test_combo.configure(state="disabled")
            self.battery_combo.configure(state="disabled")
        else:
            self.radio_single.configure(state="normal")
            self.radio_battery.configure(state="normal")
            self.test_combo.configure(state="disabled" if not self.test_names else "normal")
            self.battery_combo.configure(state="disabled" if not self.battery_names else "normal")
            
        self.validate_inputs()

    def on_mode_changed(self):
        mode = self.mode_var.get()
        if mode == "single":
            self.procedure_lbl.configure(text="4. Select Test Template")
            self.battery_combo.pack_forget()
            self.test_combo.pack(pady=(0, 20), padx=20, anchor="w")
            self.app.selected_battery = None
            self.app.battery_items = []
            self.on_test_selected(self.test_name_var.get())
        else:
            self.procedure_lbl.configure(text="4. Select Test Battery")
            self.test_combo.pack_forget()
            self.battery_combo.pack(pady=(0, 20), padx=20, anchor="w")
            self.app.selected_test_def = None
            self.on_battery_selected(self.battery_name_var.get())

    def on_battery_selected(self, battery_name):
        battery = self.battery_map.get(battery_name)
        self.app.selected_battery = battery
        if battery:
            self.app.battery_items = self.app.db.get_battery_items(battery.id)
            if self.app.battery_items:
                self.app.selected_test_def = self.app.battery_items[0].test_def
            else:
                self.app.selected_test_def = None
        else:
            self.app.battery_items = []
            self.app.selected_test_def = None
        self.validate_inputs()

    def on_test_selected(self, test_name):
        test_def = self.test_def_map.get(test_name)
        self.app.selected_test_def = test_def
        self.validate_inputs()

    def validate_inputs(self):
        workbench = self.workbench_var.get().strip()
        driver = self.app.selected_driver
        mode = self.mode_var.get()
        
        if mode == "single":
            test_def = self.app.selected_test_def
            is_valid = bool(workbench and driver and test_def)
        else:
            battery = self.app.selected_battery
            is_valid = bool(workbench and driver and battery and self.app.battery_items)
            
        if is_valid:
            self.start_btn.configure(state="normal")
        else:
            self.start_btn.configure(state="disabled")

    def start_session(self):
        workbench = self.workbench_var.get().strip()
        self.app.update_workbench(workbench)
        
        mode = self.mode_var.get()
        if mode == "single":
            self.app.selected_battery = None
            self.app.battery_items = []
            self.app.show_view(TestRunnerView)
        else:
            from views.battery_runner import BatteryRunnerView
            self.app.current_battery_step = 0
            if self.app.battery_items:
                self.app.selected_test_def = self.app.battery_items[0].test_def
            self.app.show_view(BatteryRunnerView)

    def on_global_key(self, event):
        # Only parse keypresses if the dashboard view is active
        if getattr(self.app, "current_view", None) is not self:
            return

        import time
        now = time.time()
        char = event.char
        keysym = event.keysym
        
        if keysym == "Return":
            if self._scan_buffer:
                scanned_val = "".join(self._scan_buffer).strip()
                self._scan_buffer.clear()
                
                # Check if it corresponds to an active torque driver
                driver = self.app.db.get_driver_by_tag(scanned_val)
                if driver:
                    self.driver_id_var.set(driver.driver_id)
                    self.on_driver_selected(driver.driver_id)
                    logger.info(f"Barcode Scanner: Auto-selected Torque Driver '{driver.driver_id}'")
            return
            
        # Differentiate rapid hardware input from manual typing (USB HID keyboard emulation)
        if char and char.isprintable():
            # If the duration since last keystroke is large, reset buffer (it was manual typing or a new scan)
            if now - self._last_scan_time > 0.08:  # 80ms threshold
                self._scan_buffer = [char]
            else:
                self._scan_buffer.append(char)
            self._last_scan_time = now

    def destroy(self):
        try:
            self.winfo_toplevel().unbind("<Key>")
        except Exception:
            pass
        super().destroy()
