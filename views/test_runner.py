import customtkinter as ctk
import time
from utils.logger import get_logger, log_action
from utils.helpers import check_tolerance
from views.components import TorqueGauge, ScrollableTable

logger = get_logger()

class TestRunnerView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Verify setup state
        if not self.app.selected_driver or not self.app.selected_test_def or not self.app.selected_workbench:
            # Show redirect warning
            self.show_error_redirect()
            return
            
        self.driver = self.app.selected_driver
        self.test_def = self.app.selected_test_def
        self.workbench = self.app.selected_workbench
        
        # Test progress state
        self.current_sample_idx = 0
        self.measurements = []  # list of floats
        self.session_id = None
        self.is_active = True
        self.auto_capture_state = "IDLE"
        self.tracked_peak = 0.0
        
        # Grid layout (2 columns: left details/controls, right gauge/samples)
        self.grid_columnconfigure(0, weight=1, uniform="cols")
        self.grid_columnconfigure(1, weight=1, uniform="cols")
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: Instructions & Details ---
        self.left_panel = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.left_panel.grid_columnconfigure(0, weight=1)
        
        # Test Details
        lbl = ctk.CTkLabel(self.left_panel, text="TEST RUNNER", font=ctk.CTkFont(size=18, weight="bold"))
        lbl.pack(pady=(20, 10), padx=20, anchor="w")
        
        hand_str = "Left (CCW)" if getattr(self.driver, 'handedness', 'right') == 'left' else "Right (CW)"
        tester_id = getattr(self.test_def, 'default_tester_id', 'A')
        suffix = "" if tester_id == "A" else (f"_b" if tester_id == "B" else f"_{tester_id.lower()}")
        settings_key = f"tester_model{suffix}"
        tester_model = self.app.hw_config.get_setting(settings_key, "ng-TTS50-xu")
        if tester_model == "Custom…":
            model_disp = self.app.hw_config.get_setting(f"custom_model_name{suffix}", "Custom Tester")
        else:
            model_disp = tester_model
        tester_name = f"Tester {tester_id} ({model_disp})"
        info_str = (
            f"Driver ID: {self.driver.driver_id} ({self.driver.brand} {self.driver.model})\n"
            f"Handedness: {hand_str}\n"
            f"Active Tester: {tester_name}\n"
            f"Workbench: {self.workbench}\n"
            f"Target Torque: {self.test_def.target_value} cNm\n"
            f"Tolerance: +{self.test_def.tolerance_plus} / -{self.test_def.tolerance_minus} cNm\n"
            f"Required Samples: {self.test_def.min_samples} to {self.test_def.num_samples}"
        )
        self.info_lbl = ctk.CTkLabel(
            self.left_panel, 
            text=info_str, 
            font=ctk.CTkFont(size=12),
            text_color="gray80",
            justify="left",
            anchor="w"
        )
        self.info_lbl.pack(padx=20, pady=10, fill="x")
        
        # Instructions Box
        inst_title = ctk.CTkLabel(self.left_panel, text="OPERATOR INSTRUCTIONS", font=ctk.CTkFont(size=12, weight="bold"))
        inst_title.pack(pady=(15, 2), padx=20, anchor="w")
        
        self.instructions_box = ctk.CTkTextbox(self.left_panel, height=120, activate_scrollbars=True)
        self.instructions_box.pack(fill="x", padx=20, pady=(0, 15))
        self.instructions_box.insert("1.0", self.test_def.instructions or "Execute the test steps as required.")
        self.instructions_box.configure(state="disabled")
        
        # Control Buttons
        self.btn_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=10)
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.capture_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Capture Value", 
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(weight="bold"),
            command=self.capture_sample
        )
        self.capture_btn.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.reset_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Reset Peak", 
            height=40,
            fg_color="gray25",
            hover_color="gray35",
            command=self.reset_sensor_peak
        )
        self.reset_btn.grid(row=0, column=1, padx=(5, 0), pady=5, sticky="ew")
        
        self.discard_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Discard Last", 
            height=30,
            fg_color="gray30",
            state="disabled",
            command=self.discard_last_sample
        )
        self.discard_btn.grid(row=1, column=0, padx=(0, 5), pady=10, sticky="ew")

        self.finish_btn = ctk.CTkButton(
            self.btn_frame,
            text="Finish Test",
            height=30,
            fg_color="gray30",
            state="disabled",
            command=self.finish_test
        )
        self.finish_btn.grid(row=1, column=1, padx=(5, 0), pady=10, sticky="ew")

        # Auto Capture Checkbox
        self.auto_capture_var = ctk.BooleanVar(value=True)
        self.auto_capture_cb = ctk.CTkCheckBox(
            self.left_panel,
            text="Auto Capture Peak (on Snap-Back)",
            variable=self.auto_capture_var,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.auto_capture_cb.pack(pady=(5, 10), padx=20, anchor="w")
        
        self.abort_btn = ctk.CTkButton(
            self.left_panel, 
            text="Abort Test", 
            height=35,
            fg_color="red4",
            hover_color="red3",
            command=self.abort_test
        )
        self.abort_btn.pack(side="bottom", fill="x", padx=20, pady=20)
        
        # --- RIGHT PANEL: Visual Gauge & Sample Progress ---
        self.right_panel = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.right_panel.grid_columnconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(2, weight=1) # Table takes remaining space
        
        # Visual Gauge (displays 0 to 50 or 0 to max_val based on test limits)
        tester_id = getattr(self.test_def, 'default_tester_id', 'A')
        suffix = "" if tester_id == "A" else (f"_b" if tester_id == "B" else f"_{tester_id.lower()}")
        settings_key = f"tester_model{suffix}"
        tester_model = self.app.hw_config.get_setting(settings_key, "ng-TTS50-xu")
        if tester_model == "Custom…":
            max_limit = float(self.app.hw_config.get_setting(f"custom_torque_max{suffix}", 50.0))
        else:
            max_limit = 500.0 if "500" in tester_model else 50.0

        self.gauge = TorqueGauge(
            self.right_panel, 
            min_val=0.0, 
            max_val=max_limit,
            target=self.test_def.target_value,
            tol_plus=self.test_def.tolerance_plus,
            tol_minus=self.test_def.tolerance_minus,
            fg_color="transparent"
        )
        self.gauge.grid(row=0, column=0, pady=10, sticky="ew")
        
        # Sample progress indicator
        self.progress_lbl = ctk.CTkLabel(
            self.right_panel, 
            text=f"PROGRESS: Sample 1 of {self.test_def.num_samples} (Min: {self.test_def.min_samples})", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.progress_lbl.grid(row=1, column=0, pady=5, sticky="ew")
        
        # Measurements List Table
        self.table = ScrollableTable(
            self.right_panel,
            headers=["Sample", "Measured (cNm)", "Limit Check", "Status"],
            column_weights=[1, 2, 2, 2],
            fg_color="transparent"
        )
        self.table.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="nsew")
        
        # Start DB Session
        self.db_start_session()
        
        # Start sensor reading loop
        self.poll_sensor()
        
        # Trigger initial simulated cycle if simulator is active
        self.trigger_simulated_torque()

    def show_error_redirect(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(self, width=400, height=200, corner_radius=10, fg_color="gray15")
        card.grid(row=0, column=0)
        
        lbl = ctk.CTkLabel(card, text="Incomplete Session Parameters!", font=ctk.CTkFont(size=16, weight="bold"), text_color="red")
        lbl.pack(pady=30, padx=20)
        
        btn = ctk.CTkButton(card, text="Go to Dashboard", command=lambda: self.app.show_view(self.app.nav_buttons[0])) # fallback
        btn.pack(pady=10)
        # Actually go back to dashboard safely
        from views.dashboard import DashboardView
        btn.configure(command=lambda: self.app.show_view(DashboardView))

    def db_start_session(self):
        """Create a session entry in the database."""
        self.session_id = self.app.db.start_test_session(
            driver_id=self.driver.id,
            test_def_id=self.test_def.id,
            workbench=self.workbench,
            operator_id=self.app.user_manager.current_user.id
        )
        log_action(self.app.user_manager.current_user.username, "START_TEST_SESSION", f"Session {self.session_id} for driver {self.driver.driver_id}")

    def poll_sensor(self):
        """Continually read current and peak values from the sensor."""
        if not self.is_active or not self.app.sensor:
            return
            
        current = self.app.sensor.read_torque()
        peak = self.app.sensor.get_peak()
        
        # UI updates always use absolute magnitude
        abs_current = abs(current)
        abs_peak = abs(peak)
        
        self.gauge.update_values(abs_current, abs_peak)

        # Auto-capture logic works on absolute value magnitude
        if self.auto_capture_var.get():
            target_value = self.test_def.target_value
            start_threshold = max(0.5, 0.15 * target_value)
            reset_threshold = max(0.3, 0.08 * target_value)
            
            if self.auto_capture_state == "IDLE":
                if abs_current >= start_threshold:
                    self.auto_capture_state = "RISING"
                    self.tracked_peak = abs_current
            elif self.auto_capture_state == "RISING":
                if abs_current > self.tracked_peak:
                    self.tracked_peak = abs_current
                
                # Check for snap back (15% drop from peak and at least 0.5 cNm drop)
                if abs_current < self.tracked_peak * 0.85 and (self.tracked_peak - abs_current >= 0.5):
                    self.auto_capture_state = "CAPTURED"
                    self.capture_sample(self.tracked_peak)
            elif self.auto_capture_state == "CAPTURED":
                if abs_current < reset_threshold:
                    self.auto_capture_state = "IDLE"
                    self.tracked_peak = 0.0
        
        # Schedule next poll
        self.after(50, self.poll_sensor)

    def trigger_simulated_torque(self):
        """Helper to start simulator push if using simulator."""
        if hasattr(self.app.sensor, "start_torque_cycle"):
            self.app.sensor.start_torque_cycle(self.test_def.target_value)

    def reset_sensor_peak(self):
        if self.app.sensor:
            self.app.sensor.reset_peak()
            self.auto_capture_state = "IDLE"
            self.tracked_peak = 0.0
            self.trigger_simulated_torque()

    def capture_sample(self, val=None):
        if not self.is_active or not self.app.sensor:
            return
            
        # Get peak value as the measurement
        measured_val = val if val is not None else self.app.sensor.get_peak()
        abs_val = abs(measured_val)
        is_lh = getattr(self.driver, 'handedness', 'right') == 'left'
        signed_val = -abs_val if is_lh else abs_val
        
        # Check against tolerance (always uses positive target and absolute measurement value)
        is_ok, low, high = check_tolerance(
            abs_val, 
            self.test_def.target_value, 
            self.test_def.tolerance_plus, 
            self.test_def.tolerance_minus
        )
        
        result_str = "OK" if is_ok else "NOK"
        
        # Record sample
        self.measurements.append(signed_val)
        self.current_sample_idx += 1
        
        # Append to visual table (table shows absolute magnitude for operator clarity)
        status_color = "green" if is_ok else "red"
        limit_check_text = f"{low:.2f} to {high:.2f}"
        
        self.table.add_row(
            [f"#{self.current_sample_idx}", f"{abs_val:.2f}", limit_check_text, result_str],
            text_color=status_color
        )
        
        # Add measurement to DB (DB stores the raw signed value)
        self.app.db.add_measurement(self.session_id, self.current_sample_idx, signed_val, result_str)
        
        # Enable discard button
        self.discard_btn.configure(state="normal")
        
        # Enable finish button if minimum samples requirement met
        if self.current_sample_idx >= self.test_def.min_samples:
            self.finish_btn.configure(state="normal", fg_color="blue", hover_color="darkblue")
        else:
            self.finish_btn.configure(state="disabled", fg_color="gray30")

        # Reset peak automatically for next sample
        self.app.sensor.reset_peak()
        
        # Check if test procedure is complete
        if self.current_sample_idx >= self.test_def.num_samples:
            self.finish_test()
        else:
            # Prepare next sample
            self.progress_lbl.configure(text=f"PROGRESS: Sample {self.current_sample_idx + 1} of {self.test_def.num_samples} (Min: {self.test_def.min_samples})")
            self.trigger_simulated_torque()

    def discard_last_sample(self):
        """Discard the last recorded measurement and reset state to retake it."""
        if not self.measurements or not self.is_active:
            return
            
        # Remove last record from local array
        discarded_val = self.measurements.pop()
        
        # SQLite measurements are linked to session, we can delete the row from DB
        # For simplicity, we just delete the last record in db for this session
        try:
            with self.app.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM test_measurements WHERE session_id = ? AND sample_number = ?",
                    (self.session_id, self.current_sample_idx)
                )
                conn.commit()
            logger.info(f"Discarded sample #{self.current_sample_idx} ({discarded_val} cNm) from DB.")
        except Exception as e:
            logger.error(f"Error deleting discarded measurement: {e}")
            
        self.current_sample_idx -= 1
        
        # Redraw table rows from scratch
        self.table.clear()
        for idx, val in enumerate(self.measurements):
            is_ok, low, high = check_tolerance(
                val, 
                self.test_def.target_value, 
                self.test_def.tolerance_plus, 
                self.test_def.tolerance_minus
            )
            res = "OK" if is_ok else "NOK"
            self.table.add_row(
                [f"#{idx + 1}", f"{val:.2f}", f"{low:.2f} to {high:.2f}", res],
                text_color="green" if is_ok else "red"
            )
            
        # Update labels
        self.progress_lbl.configure(text=f"PROGRESS: Sample {self.current_sample_idx + 1} of {self.test_def.num_samples} (Min: {self.test_def.min_samples})")
        
        if not self.measurements:
            self.discard_btn.configure(state="disabled")
            
        # Enable finish button if minimum samples requirement met
        if self.current_sample_idx >= self.test_def.min_samples:
            self.finish_btn.configure(state="normal", fg_color="blue", hover_color="darkblue")
        else:
            self.finish_btn.configure(state="disabled", fg_color="gray30")

        # Reset auto-capture and sensor peak state for retake
        self.auto_capture_state = "IDLE"
        self.tracked_peak = 0.0
        self.app.sensor.reset_peak()
        self.trigger_simulated_torque()

    def finish_test(self):
        """Evaluate final overall test result and finalize session."""
        self.is_active = False
        
        # Count OK measurements
        ok_count = 0
        for val in self.measurements:
            is_ok, _, _ = check_tolerance(
                abs(val), 
                self.test_def.target_value, 
                self.test_def.tolerance_plus, 
                self.test_def.tolerance_minus
            )
            if is_ok:
                ok_count += 1
                
        # Resolve min_ok_samples limit
        min_ok = self.test_def.min_ok_samples if self.test_def.min_ok_samples is not None else self.test_def.num_samples
        overall_result = "PASS" if ok_count >= min_ok else "FAIL"
        
        # Write to Database
        self.app.db.complete_test_session(self.session_id, overall_result)
        log_action(self.app.user_manager.current_user.username, "COMPLETE_TEST_SESSION", f"Session {self.session_id} ended with {overall_result} ({ok_count}/{self.current_sample_idx} OK)")
        
        # Visual styling based on result
        result_color = "green" if overall_result == "PASS" else "red"
        self.progress_lbl.configure(
            text=f"SESSION COMPLETED: {overall_result} ({ok_count}/{self.current_sample_idx} OK)", 
            text_color=result_color
        )
        
        # Change button states
        self.capture_btn.configure(state="disabled")
        self.reset_btn.configure(state="disabled")
        self.discard_btn.configure(state="disabled")
        self.finish_btn.configure(state="disabled")
        
        # Change Abort to Finish
        self.abort_btn.configure(
            text="Done - Return to Dashboard", 
            fg_color="green" if overall_result == "PASS" else "gray30",
            hover_color="darkgreen" if overall_result == "PASS" else "gray40",
            command=self.return_to_dashboard
        )

    def abort_test(self):
        """Abort without updating results, session left as ABORTED."""
        if self.session_id:
            self.app.db.complete_test_session(self.session_id, "ABORTED")
            log_action(self.app.user_manager.current_user.username, "ABORT_TEST_SESSION", f"Session {self.session_id} aborted by operator")
            
        self.is_active = False
        self.return_to_dashboard()

    def return_to_dashboard(self):
        self.is_active = False
        
        # Reset app setup parameters
        self.app.selected_driver = None
        self.app.selected_test_def = None
        
        # Load dashboard view
        from views.dashboard import DashboardView
        self.app.show_view(DashboardView)
