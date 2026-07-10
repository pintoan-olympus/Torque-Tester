import customtkinter as ctk
import time
from datetime import datetime
from utils.logger import get_logger, log_action
from utils.helpers import check_tolerance
from views.components import ScrollableTable

logger = get_logger()

class TestRunnerView(ctk.CTkFrame):
    def __init__(self, master, app, step_number=1, total_steps=1, on_step_complete=None):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.step_number = step_number
        self.total_steps = total_steps
        self.on_step_complete = on_step_complete

        # Verify setup state
        if not self.app.selected_driver or not self.app.selected_test_def or not self.app.selected_workbench:
            self.show_error_redirect()
            return
            
        self.driver = self.app.selected_driver
        self.test_def = self.app.selected_test_def
        self.workbench = self.app.selected_workbench
        
        # Test progress state
        self.current_sample_idx = 0
        self.measurements = []  # list of signed floats
        self.session_id = None
        self.is_active = False  # Set to True when "Start Measurements" is clicked
        self.auto_capture_state = "IDLE"
        self.tracked_peak = 0.0
        self.polling_started = False
        
        # Grid layout for center alignment
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Centering Container
        self.container = ctk.CTkFrame(self, corner_radius=12, fg_color="gray15")
        self.container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1) # Main area takes space

        # --- HEADER AREA ---
        self.header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text=self.test_def.name, 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.title_lbl.pack(side="left")

        # Step Badge
        badge_text = f"Test {self.step_number} of {self.total_steps}"
        self.badge_lbl = ctk.CTkLabel(
            self.header_frame,
            text=badge_text,
            fg_color="gray25",
            corner_radius=6,
            padx=10,
            pady=4,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.badge_lbl.pack(side="right")

        # --- CONTENT CONTAINER (Swapped between measurement screen and result screen) ---
        self.content_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Build individual screens
        self.build_measurement_screen()
        self.build_result_screen()

        # Show initial screen
        self.show_measurement_screen()

        # Start DB Session
        self.db_start_session()

    def show_error_redirect(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(self, width=400, height=200, corner_radius=10, fg_color="gray15")
        card.grid(row=0, column=0)
        
        lbl = ctk.CTkLabel(card, text="Incomplete Session Parameters!", font=ctk.CTkFont(size=16, weight="bold"), text_color="red")
        lbl.pack(pady=30, padx=20)
        
        from views.dashboard import DashboardView
        btn = ctk.CTkButton(card, text="Go to Dashboard", command=lambda: self.app.show_view(DashboardView))
        btn.pack(pady=10)

    def db_start_session(self):
        """Create a session entry in the database."""
        self.session_id = self.app.db.start_test_session(
            driver_id=self.driver.id,
            test_def_id=self.test_def.id,
            workbench=self.workbench,
            operator_id=self.app.user_manager.current_user.id
        )
        log_action(self.app.user_manager.current_user.username, "START_TEST_SESSION", f"Session {self.session_id} for driver {self.driver.driver_id}")

    def build_measurement_screen(self):
        """Setup measurement screen elements (packed into self.measurement_card)."""
        self.measurement_card = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.measurement_card.grid(row=0, column=0, sticky="nsew")
        self.measurement_card.grid_columnconfigure(0, weight=1)
        self.measurement_card.grid_rowconfigure(4, weight=1) # Table takes rest of space

        # 1. Instructions and Target details
        inst_card = ctk.CTkFrame(self.measurement_card, fg_color="gray12", corner_radius=8)
        inst_card.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        target_info = f"Target: {self.test_def.target_value:.2f} cNm (Tolerance: +{self.test_def.tolerance_plus:.2f} / -{self.test_def.tolerance_minus:.2f} cNm)"
        t_lbl = ctk.CTkLabel(inst_card, text=target_info, font=ctk.CTkFont(size=14, weight="bold"), text_color="orange")
        t_lbl.pack(padx=20, pady=(15, 5), anchor="w")
        
        inst_text = self.test_def.instructions or "Please perform the torque verification sequence."
        inst_lbl = ctk.CTkLabel(inst_card, text=inst_text, font=ctk.CTkFont(size=12), text_color="gray80", justify="left", anchor="w", wraplength=700)
        inst_lbl.pack(padx=20, pady=(0, 15), anchor="w")

        # 2. Live Reading & Status (Hidden until Start is clicked)
        self.live_feed_frame = ctk.CTkFrame(self.measurement_card, fg_color="transparent")
        self.live_feed_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        # Center container for large labels
        lf_inner = ctk.CTkFrame(self.live_feed_frame, fg_color="gray10", corner_radius=8)
        lf_inner.pack(fill="x", padx=10, pady=5)
        
        self.live_lbl = ctk.CTkLabel(lf_inner, text="Live Reading: --- cNm", font=ctk.CTkFont(size=18, weight="bold"), text_color="cyan")
        self.live_lbl.pack(side="left", expand=True, pady=15)
        
        self.peak_lbl = ctk.CTkLabel(lf_inner, text="Peak: --- cNm", font=ctk.CTkFont(size=18, weight="bold"), text_color="yellow")
        self.peak_lbl.pack(side="left", expand=True, pady=15)

        # 3. Control Buttons Area
        self.controls_frame = ctk.CTkFrame(self.measurement_card, fg_color="transparent")
        self.controls_frame.grid(row=2, column=0, sticky="ew", pady=10)

        # Start Measurements button (visible initially, covers other buttons)
        self.start_meas_btn = ctk.CTkButton(
            self.controls_frame, 
            text="Start Measurements", 
            height=45,
            fg_color="blue",
            hover_color="darkblue",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.start_measurements
        )
        self.start_meas_btn.pack(fill="x", padx=10, pady=5)

        # Action Buttons frame (hidden initially)
        self.act_buttons_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        
        self.capture_btn = ctk.CTkButton(
            self.act_buttons_frame, 
            text="Capture Value", 
            height=40,
            fg_color="green",
            hover_color="darkgreen",
            font=ctk.CTkFont(weight="bold"),
            command=self.capture_sample
        )
        self.capture_btn.pack(side="left", fill="x", expand=True, padx=5)

        self.reset_btn = ctk.CTkButton(
            self.act_buttons_frame, 
            text="Reset Peak", 
            height=40,
            fg_color="gray25",
            hover_color="gray35",
            command=self.reset_sensor_peak
        )
        self.reset_btn.pack(side="left", fill="x", expand=True, padx=5)

        self.discard_btn = ctk.CTkButton(
            self.act_buttons_frame, 
            text="Discard Last", 
            height=40,
            fg_color="gray30",
            state="disabled",
            command=self.discard_last_sample
        )
        self.discard_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Progress / Settings bar
        self.progress_bar_frame = ctk.CTkFrame(self.measurement_card, fg_color="transparent")
        self.progress_bar_frame.grid(row=3, column=0, sticky="ew", pady=5)

        self.progress_lbl = ctk.CTkLabel(
            self.progress_bar_frame, 
            text=f"PROGRESS: Sample 1 of {self.test_def.num_samples} (Min: {self.test_def.min_samples})", 
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.progress_lbl.pack(side="left", padx=10)

        # Dots representation
        self.dots_lbl = ctk.CTkLabel(
            self.progress_bar_frame,
            text=self.get_progress_dots(),
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="orange"
        )
        self.dots_lbl.pack(side="left", padx=10)

        # Auto capture checkbox
        self.auto_capture_var = ctk.BooleanVar(value=True)
        self.auto_capture_cb = ctk.CTkCheckBox(
            self.progress_bar_frame,
            text="Auto Capture Snap-Back",
            variable=self.auto_capture_var,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.auto_capture_cb.pack(side="right", padx=10)

        # 4. Table Log
        self.table = ScrollableTable(
            self.measurement_card,
            headers=["Sample", "Measured (cNm)", "Limit Check", "Status"],
            column_weights=[1, 2, 2, 2],
            fg_color="transparent"
        )
        self.table.grid(row=4, column=0, sticky="nsew", padx=10, pady=(10, 0))

        # Bottom Abort Button
        self.abort_btn = ctk.CTkButton(
            self.measurement_card, 
            text="Abort Test", 
            height=35,
            fg_color="red4",
            hover_color="red3",
            command=self.abort_test
        )
        self.abort_btn.grid(row=5, column=0, sticky="ew", pady=(15, 0), padx=10)

    def start_measurements(self):
        """Action when operator clicks 'Start Measurements'."""
        self.is_active = True
        self.start_meas_btn.pack_forget()
        self.act_buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Start sensor reading loop
        if not self.polling_started:
            self.polling_started = True
            self.poll_sensor()
            
        self.trigger_simulated_torque()
        logger.info("TestRunnerView: Measurements loop activated by operator.")

    def get_progress_dots(self) -> str:
        dots = ""
        for i in range(self.test_def.num_samples):
            if i < self.current_sample_idx:
                dots += "●"
            else:
                dots += "○"
        return dots

    def build_result_screen(self):
        """Setup result screen elements (packed into self.result_card)."""
        self.result_card = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.result_card.grid_columnconfigure(0, weight=1)
        self.result_card.grid_rowconfigure(2, weight=1) # Summary table takes space

        # Result Header Card
        self.res_banner = ctk.CTkFrame(self.result_card, corner_radius=10)
        self.res_banner.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        self.res_title = ctk.CTkLabel(
            self.res_banner, 
            text="TEST COMPLETED", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color="white"
        )
        self.res_title.pack(pady=(15, 5))

        self.res_sub = ctk.CTkLabel(
            self.res_banner, 
            text="Result Summary", 
            font=ctk.CTkFont(size=13), 
            text_color="white"
        )
        self.res_sub.pack(pady=(0, 10))

        # Supervisor warning label
        self.sup_lbl = ctk.CTkLabel(
            self.res_banner, 
            text="⚠️ Report test result to supervisor. DO NOT USE THE DRIVER!",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="red"
        )
        # Packed dynamically based on failure

        # Action Buttons for Result Screen
        self.res_btn_frame = ctk.CTkFrame(self.result_card, fg_color="transparent")
        self.res_btn_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        self.save_return_btn = ctk.CTkButton(
            self.res_btn_frame,
            text="Save & Return to Menu",
            height=45,
            fg_color="blue",
            hover_color="darkblue",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.save_and_finish
        )
        self.save_return_btn.pack(side="left", fill="x", expand=True, padx=5)

        self.retry_btn = ctk.CTkButton(
            self.res_btn_frame,
            text="Retry This Test",
            height=45,
            fg_color="gray25",
            hover_color="gray35",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.retry_test
        )
        self.retry_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Summary Table
        self.summary_table = ScrollableTable(
            self.result_card,
            headers=["Sample", "Measured (cNm)", "Target/Limits", "Result"],
            column_weights=[1, 2, 2, 2],
            fg_color="transparent"
        )
        self.summary_table.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

    def show_measurement_screen(self):
        self.result_card.grid_forget()
        self.measurement_card.grid(row=0, column=0, sticky="nsew")

    def show_result_screen(self, overall_result, ok_count):
        self.measurement_card.grid_forget()
        self.result_card.grid(row=0, column=0, sticky="nsew")

        # Visual styling based on result
        if overall_result == "PASS":
            self.res_banner.configure(fg_color="green")
            self.res_title.configure(text="✅ TEST PASSED", text_color="white")
            self.res_sub.configure(text=f"Driver passes verification criteria. ({ok_count}/{self.current_sample_idx} OK)", text_color="white")
            self.sup_lbl.pack_forget()
            self.save_return_btn.configure(fg_color="green", hover_color="darkgreen")
        else:
            self.res_banner.configure(fg_color="red4")
            self.res_title.configure(text="❌ TEST FAILED", text_color="white")
            self.res_sub.configure(text=f"Failed to meet minimum pass criteria of {self.test_def.min_ok_samples or self.test_def.min_samples} OK samples. ({ok_count}/{self.current_sample_idx} OK)", text_color="white")
            self.sup_lbl.pack(pady=(5, 10))
            self.save_return_btn.configure(fg_color="red", hover_color="red4")

        # Load measurements into summary table
        self.summary_table.clear()
        for idx, val in enumerate(self.measurements):
            abs_val = abs(val)
            is_ok, low, high = check_tolerance(
                abs_val, 
                self.test_def.target_value, 
                self.test_def.tolerance_plus, 
                self.test_def.tolerance_minus
            )
            res = "OK" if is_ok else "NOK"
            self.summary_table.add_row(
                [f"#{idx + 1}", f"{abs_val:.2f}", f"{low:.2f} to {high:.2f}", res],
                text_color="green" if is_ok else "red"
            )

    def poll_sensor(self):
        """Continually read current and peak values from the sensor."""
        if not self.is_active or not self.app.sensor:
            # Re-schedule next poll anyway, but skip processing
            self.after(50, self.poll_sensor)
            return
            
        current = self.app.sensor.read_torque()
        peak = self.app.sensor.get_peak()
        
        # UI updates always use absolute magnitude
        abs_current = abs(current)
        abs_peak = abs(peak)
        
        self.live_lbl.configure(text=f"Live Reading: {abs_current:.2f} cNm")
        self.peak_lbl.configure(text=f"Peak: {abs_peak:.2f} cNm")

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
            self.peak_lbl.configure(text="Peak: 0.00 cNm")

    def capture_sample(self, val=None):
        if not self.is_active or not self.app.sensor:
            return
            
        # Get peak value as the measurement
        measured_val = val if val is not None else self.app.sensor.get_peak()
        abs_val = abs(measured_val)
        is_lh = getattr(self.driver, 'handedness', 'right') == 'left'
        signed_val = -abs_val if is_lh else abs_val
        
        # Check against tolerance
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
        
        # Append to visual table
        status_color = "green" if is_ok else "red"
        limit_check_text = f"{low:.2f} to {high:.2f}"
        
        self.table.add_row(
            [f"#{self.current_sample_idx}", f"{abs_val:.2f}", limit_check_text, result_str],
            text_color=status_color
        )
        
        # Add measurement to DB
        self.app.db.add_measurement(self.session_id, self.current_sample_idx, signed_val, result_str)
        
        # Enable discard button
        self.discard_btn.configure(state="normal")
        
        # Update progress labels
        self.dots_lbl.configure(text=self.get_progress_dots())

        # Check if test procedure is complete
        if self.current_sample_idx >= self.test_def.num_samples:
            self.finish_test()
        else:
            # Prepare next sample
            self.progress_lbl.configure(text=f"PROGRESS: Sample {self.current_sample_idx + 1} of {self.test_def.num_samples} (Min: {self.test_def.min_samples})")
            self.app.sensor.reset_peak()
            self.trigger_simulated_torque()

    def discard_last_sample(self):
        """Discard the last recorded measurement and reset state to retake it."""
        if not self.measurements or not self.is_active:
            return
            
        # Remove last record from local array
        discarded_val = self.measurements.pop()
        
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
            abs_val = abs(val)
            is_ok, low, high = check_tolerance(
                abs_val, 
                self.test_def.target_value, 
                self.test_def.tolerance_plus, 
                self.test_def.tolerance_minus
            )
            res = "OK" if is_ok else "NOK"
            self.table.add_row(
                [f"#{idx + 1}", f"{abs_val:.2f}", f"{low:.2f} to {high:.2f}", res],
                text_color="green" if is_ok else "red"
            )
            
        # Update labels
        self.progress_lbl.configure(text=f"PROGRESS: Sample {self.current_sample_idx + 1} of {self.test_def.num_samples} (Min: {self.test_def.min_samples})")
        self.dots_lbl.configure(text=self.get_progress_dots())

        if not self.measurements:
            self.discard_btn.configure(state="disabled")
            
        # Reset auto-capture and sensor peak state for retake
        self.auto_capture_state = "IDLE"
        self.tracked_peak = 0.0
        self.app.sensor.reset_peak()
        self.trigger_simulated_torque()

    def finish_test(self):
        """Evaluate final overall test result and display result screen."""
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
                
        min_ok = self.test_def.min_ok_samples if self.test_def.min_ok_samples is not None else self.test_def.num_samples
        self.overall_result = "PASS" if ok_count >= min_ok else "FAIL"
        
        if self.on_step_complete:
            self.save_and_finish()
        else:
            self.show_result_screen(self.overall_result, ok_count)

    def save_and_finish(self):
        """Finalize DB records and trigger completion callbacks."""
        self.is_active = False
        
        # Complete DB Session
        self.app.db.complete_test_session(self.session_id, self.overall_result)
        log_action(
            self.app.user_manager.current_user.username, 
            "COMPLETE_TEST_SESSION", 
            f"Session {self.session_id} ended with {self.overall_result}"
        )
        
        if self.on_step_complete:
            # If in a battery, call callback to progress
            self.on_step_complete(self.overall_result, self.session_id)
        else:
            # Standalone mode: return to dashboard
            self.return_to_dashboard()

    def retry_test(self):
        """Discard current session (marks it as ABORTED) and starts a new one."""
        self.is_active = False
        
        # Abort the previous database session
        if self.session_id:
            self.app.db.complete_test_session(self.session_id, "ABORTED")
            log_action(
                self.app.user_manager.current_user.username, 
                "ABORT_TEST_SESSION", 
                f"Session {self.session_id} aborted by operator for retry"
            )
            
        # Reset local runner states
        self.current_sample_idx = 0
        self.measurements = []
        self.table.clear()
        
        # UI updates
        self.progress_lbl.configure(text=f"PROGRESS: Sample 1 of {self.test_def.num_samples} (Min: {self.test_def.min_samples})")
        self.dots_lbl.configure(text=self.get_progress_dots())
        self.live_lbl.configure(text="Live Reading: --- cNm")
        self.peak_lbl.configure(text="Peak: --- cNm")
        
        self.start_meas_btn.pack(fill="x", padx=10, pady=5)
        self.act_buttons_frame.pack_forget()
        self.discard_btn.configure(state="disabled")
        
        self.show_measurement_screen()
        
        # Restart DB session
        self.db_start_session()
        self.reset_sensor_peak()

    def abort_test(self):
        """Abort without updating results, session left as ABORTED."""
        self.is_active = False
        if self.session_id:
            self.app.db.complete_test_session(self.session_id, "ABORTED")
            log_action(self.app.user_manager.current_user.username, "ABORT_TEST_SESSION", f"Session {self.session_id} aborted by operator")
            
        if self.on_step_complete:
            self.on_step_complete("ABORTED", self.session_id)
        else:
            self.return_to_dashboard()

    def return_to_dashboard(self):
        self.is_active = False
        self.app.selected_driver = None
        self.app.selected_test_def = None
        self.app.selected_battery = None
        self.app.battery_items = []
        
        from views.dashboard import DashboardView
        self.app.show_view(DashboardView)

    def destroy(self):
        self.is_active = False
        super().destroy()
