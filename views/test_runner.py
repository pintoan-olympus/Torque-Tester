import customtkinter as ctk
import time
from datetime import datetime
from utils.logger import get_logger, log_action
from utils.helpers import check_tolerance
import i18n

logger = get_logger()

class TestRunnerView(ctk.CTkFrame):
    def __init__(self, master, app, step_number=1, total_steps=1, on_step_complete=None, battery_session_id=None):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.step_number = step_number
        self.total_steps = total_steps
        self.on_step_complete = on_step_complete
        self.battery_session_id = battery_session_id

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
        self.is_active = False  # Set to True when in Phase 2 (measuring)
        self.auto_capture_state = "IDLE"
        self.tracked_peak = 0.0
        self.polling_started = False
        self.auto_capture_var = ctk.BooleanVar(value=True)
        
        # Grid layout for center alignment
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main Centering Container
        self.container = ctk.CTkFrame(self, corner_radius=12, fg_color="gray15")
        self.container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Start by showing the instruction phase
        self.show_instruction_phase()

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
            operator_id=self.app.user_manager.current_user.id,
            battery_session_id=self.battery_session_id
        )
        log_action(self.app.user_manager.current_user.username, "START_TEST_SESSION", f"Session {self.session_id} for driver {self.driver.driver_id}")

    def clear_container(self):
        """Clean all widgets from self.container and reset row/col weights."""
        for widget in self.container.winfo_children():
            widget.destroy()
        self.container.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=0)
        self.container.grid_columnconfigure((0, 1, 2), weight=0)
        self.container.configure(fg_color="gray15")

    def show_instruction_phase(self):
        """Phase 1: SET TORQUE (Instruction card)"""
        self.is_active = False
        self.clear_container()
        
        # Grid weights for vertical centering
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure((0, 4), weight=2)
        self.container.grid_rowconfigure((1, 2, 3), weight=1)
        
        # Centered Step Badge
        lbl_badge = ctk.CTkLabel(
            self.container,
            text=i18n.t("run.test_n_of_m", n=self.step_number, m=self.total_steps),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        lbl_badge.grid(row=1, column=0, pady=(20, 10))
        
        # Card with target torque instructions
        inst_card = ctk.CTkFrame(self.container, fg_color="gray12", corner_radius=12)
        inst_card.grid(row=2, column=0, pady=10, padx=40, sticky="ew")
        
        target_val = self.test_def.target_value
        target_text = i18n.t("run.set_torque", target=f"{target_val:.2f}")
        lbl_target = ctk.CTkLabel(
            inst_card,
            text=target_text,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="orange"
        )
        lbl_target.pack(padx=20, pady=25)
        
        # Instructions details
        inst_detail = self.test_def.instructions or "Please perform the torque verification sequence."
        lbl_detail = ctk.CTkLabel(
            inst_card,
            text=inst_detail,
            font=ctk.CTkFont(size=13),
            text_color="gray70",
            wraplength=600,
            justify="center"
        )
        lbl_detail.pack(padx=20, pady=(0, 20))
        
        # Start button
        btn_start = ctk.CTkButton(
            self.container,
            text=i18n.t("run.start_btn"),
            height=50,
            width=250,
            fg_color="#00A86B",
            hover_color="#008E5A",
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.show_measuring_phase
        )
        btn_start.grid(row=3, column=0, pady=(20, 40))

    def show_measuring_phase(self):
        """Phase 2: MEASURING (Live Reading + Peak)"""
        self.clear_container()
        self.is_active = True
        
        # Start DB Session if not already started
        if self.session_id is None:
            self.db_start_session()
            
        # Grid weights
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=0)
        self.container.grid_rowconfigure(1, weight=3)
        self.container.grid_rowconfigure((2, 3), weight=1)
        
        # Header title
        header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        
        header_lbl = ctk.CTkLabel(
            header_frame,
            text=self.test_def.name,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        header_lbl.pack(side="left")
        
        badge_lbl = ctk.CTkLabel(
            header_frame,
            text=i18n.t("run.test_n_of_m", n=self.step_number, m=self.total_steps),
            fg_color="gray25",
            corner_radius=6,
            padx=10,
            pady=4,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="white"
        )
        badge_lbl.pack(side="right")
        
        # Live readouts card
        card_readouts = ctk.CTkFrame(self.container, fg_color="gray10", corner_radius=10)
        card_readouts.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        card_readouts.grid_columnconfigure((0, 1), weight=1)
        card_readouts.grid_rowconfigure(0, weight=1)
        
        # Live reading
        self.live_lbl = ctk.CTkLabel(
            card_readouts, 
            text=f"{i18n.t('run.live')}: --- cNm", 
            font=ctk.CTkFont(size=30, weight="bold"), 
            text_color="cyan"
        )
        self.live_lbl.grid(row=0, column=0, padx=20, pady=40)
        
        # Peak reading
        self.peak_lbl = ctk.CTkLabel(
            card_readouts, 
            text=f"{i18n.t('run.peak')}: 0.00 cNm", 
            font=ctk.CTkFont(size=30, weight="bold"), 
            text_color="yellow"
        )
        self.peak_lbl.grid(row=0, column=1, padx=20, pady=40)
        
        # Controls Frame
        controls_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        controls_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        controls_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.capture_btn = ctk.CTkButton(
            controls_frame,
            text=i18n.t("run.capture_btn"),
            height=45,
            fg_color="#00A86B",
            hover_color="#008E5A",
            text_color="white",
            font=ctk.CTkFont(weight="bold"),
            command=self.capture_sample
        )
        self.capture_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.reset_btn = ctk.CTkButton(
            controls_frame,
            text=i18n.t("run.reset_peak"),
            height=45,
            fg_color="gray25",
            hover_color="gray35",
            text_color="white",
            font=ctk.CTkFont(weight="bold"),
            command=self.reset_sensor_peak
        )
        self.reset_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Progress info
        prog_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        prog_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        
        prog_text = i18n.t("run.sample_n_of_m", n=self.current_sample_idx + 1, total=self.test_def.num_samples)
        self.progress_lbl = ctk.CTkLabel(
            prog_frame,
            text=prog_text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        self.progress_lbl.pack(side="left", padx=10)
        
        self.dots_lbl = ctk.CTkLabel(
            prog_frame,
            text=self.get_progress_dots(),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="orange"
        )
        self.dots_lbl.pack(side="left", padx=10)
        
        self.auto_capture_cb = ctk.CTkCheckBox(
            prog_frame,
            text="Auto Capture Snap-Back",
            variable=self.auto_capture_var,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.auto_capture_cb.pack(side="right", padx=10)
        
        # Discard or Abort button at bottom
        self.abort_btn = ctk.CTkButton(
            self.container, 
            text="Abort Test", 
            height=35,
            fg_color="red4",
            hover_color="red3",
            command=self.abort_test
        )
        self.abort_btn.grid(row=4, column=0, sticky="ew", pady=(15, 0), padx=20)
        self.container.grid_rowconfigure(4, weight=0)

        # Start polling loop
        if not self.polling_started:
            self.polling_started = True
            self.poll_sensor()
            
        self.trigger_simulated_torque()

    def show_sample_result_phase(self, val, is_ok, programmatic=False):
        """Phase 3: SAMPLE RESULT (Full-screen color bleed green/red)"""
        self.is_active = False
        self.clear_container()
        
        bg_color = "#00A86B" if is_ok else "#FF0000"
        self.container.configure(fg_color=bg_color)
        
        # Grid layout
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=3) # top colored frame
        self.container.grid_rowconfigure(1, weight=2) # bottom details card (white)
        
        # Top colored frame
        top_content = ctk.CTkFrame(self.container, fg_color="transparent")
        top_content.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        top_content.grid_columnconfigure(0, weight=1)
        top_content.grid_rowconfigure((0, 1, 2, 3), weight=1)
        
        # Badge
        badge_text = i18n.t("run.sample_n_of_m", n=self.current_sample_idx, total=self.test_def.num_samples)
        lbl_badge = ctk.CTkLabel(
            top_content,
            text=badge_text,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        lbl_badge.grid(row=0, column=0, sticky="s", pady=(10, 5))
        
        # PASS / FAIL
        res_text = i18n.t("run.result_pass") if is_ok else i18n.t("run.result_fail")
        lbl_res = ctk.CTkLabel(
            top_content,
            text=res_text,
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="white"
        )
        lbl_res.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Value details
        low = self.test_def.target_value - self.test_def.tolerance_minus
        high = self.test_def.target_value + self.test_def.tolerance_plus
        val_desc = f"{val:.2f} cNm   [{low:.2f} - {high:.2f}]"
        lbl_val = ctk.CTkLabel(
            top_content,
            text=val_desc,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        lbl_val.grid(row=2, column=0, sticky="n", pady=5)
        
        # Message / Buttons
        if is_ok:
            if programmatic:
                self.auto_advance_flow()
            else:
                info_lbl = ctk.CTkLabel(
                    top_content,
                    text=i18n.t("run.continuing"),
                    font=ctk.CTkFont(size=15, weight="bold"),
                    text_color="white"
                )
                info_lbl.grid(row=3, column=0, sticky="n", pady=5)
                # Auto-advance countdown
                self.after(1500, self.auto_advance_flow)
        else:
            info_lbl = ctk.CTkLabel(
                top_content,
                text=i18n.t("run.supervisor_warning"),
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="white"
            )
            info_lbl.grid(row=3, column=0, sticky="n", pady=5)
            
            btn_stop = ctk.CTkButton(
                top_content,
                text=i18n.t("run.stop_test"),
                height=45,
                width=180,
                fg_color="white",
                text_color="#FF0000",
                hover_color="gray90",
                font=ctk.CTkFont(size=13, weight="bold"),
                command=self.finish_test
            )
            btn_stop.grid(row=4, column=0, pady=(10, 5))
            top_content.grid_rowconfigure(4, weight=1)
            
        # Bottom Details Area
        bottom_area = ctk.CTkFrame(self.container, corner_radius=8, fg_color="white")
        bottom_area.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        bottom_area.grid_columnconfigure(0, weight=1)
        bottom_area.grid_rowconfigure(0, weight=1)
        
        # Results list
        results_list_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        results_list_frame.grid(row=0, column=0, sticky="nsw", padx=30, pady=15)
        
        for idx in range(self.test_def.num_samples):
            if idx < len(self.measurements):
                m_val = abs(self.measurements[idx])
                is_sample_ok, _, _ = check_tolerance(
                    m_val, 
                    self.test_def.target_value, 
                    self.test_def.tolerance_plus, 
                    self.test_def.tolerance_minus
                )
                status_txt = "PASS" if is_sample_ok else "FAIL"
                lbl_color = "#00A86B" if is_sample_ok else "#FF0000"
                line_text = f"{i18n.t('run.resultado_idx', idx=idx+1)}: {m_val:.2f} cNm ({status_txt})"
            elif idx == len(self.measurements) and not is_ok:
                line_text = f"{i18n.t('run.resultado_idx', idx=idx+1)}: {val:.2f} cNm (FAIL)"
                lbl_color = "#FF0000"
            else:
                line_text = f"{i18n.t('run.resultado_idx', idx=idx+1)}: PENDING"
                lbl_color = "gray40"
                
            lbl_line = ctk.CTkLabel(
                results_list_frame,
                text=line_text,
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=lbl_color
            )
            lbl_line.pack(anchor="w", pady=3)

    def auto_advance_flow(self):
        """Check if all samples are done, or continue to instructions of next sample."""
        if self.current_sample_idx >= self.test_def.num_samples:
            self.finish_test()
        else:
            self.show_instruction_phase()

    def get_progress_dots(self) -> str:
        dots = ""
        for i in range(self.test_def.num_samples):
            if i < self.current_sample_idx:
                dots += "●"
            else:
                dots += "○"
        return dots

    def show_result_screen(self, overall_result, ok_count):
        """Final Result summary screen for standalone runner."""
        self.clear_container()
        
        bg_banner_color = "#FF0000" if overall_result == "FAIL" else "#00A86B"
        self.container.configure(fg_color=bg_banner_color)
        
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=3)
        self.container.grid_rowconfigure(1, weight=2)
        
        # Top banner labels
        top_content = ctk.CTkFrame(self.container, fg_color="transparent")
        top_content.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        top_content.grid_columnconfigure(0, weight=1)
        top_content.grid_rowconfigure((0, 1, 2), weight=1)
        
        lbl_test = ctk.CTkLabel(
            top_content,
            text=self.test_def.name,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white"
        )
        lbl_test.grid(row=0, column=0, sticky="s", pady=(10, 5))
        
        res_text = i18n.t("run.result_pass") if overall_result == "PASS" else i18n.t("run.result_fail")
        lbl_res = ctk.CTkLabel(
            top_content,
            text=res_text,
            font=ctk.CTkFont(size=54, weight="bold"),
            text_color="white"
        )
        lbl_res.grid(row=1, column=0, sticky="ew", pady=5)
        
        if overall_result == "FAIL":
            info_text = i18n.t("run.supervisor_warning")
        else:
            info_text = f"({ok_count} / {self.test_def.num_samples} samples passed)"
            
        lbl_info = ctk.CTkLabel(
            top_content,
            text=info_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        lbl_info.grid(row=2, column=0, sticky="n", pady=(5, 20))
        
        # Bottom white card area
        bottom_area = ctk.CTkFrame(self.container, corner_radius=8, fg_color="white")
        bottom_area.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        bottom_area.grid_columnconfigure(0, weight=2)
        bottom_area.grid_columnconfigure(1, weight=1)
        bottom_area.grid_rowconfigure(0, weight=1)
        
        # Left results
        results_list_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        results_list_frame.grid(row=0, column=0, sticky="nsw", padx=30, pady=15)
        
        for idx in range(self.test_def.num_samples):
            if idx < len(self.measurements):
                m_val = abs(self.measurements[idx])
                is_sample_ok, _, _ = check_tolerance(
                    m_val, 
                    self.test_def.target_value, 
                    self.test_def.tolerance_plus, 
                    self.test_def.tolerance_minus
                )
                status_txt = "PASS" if is_sample_ok else "FAIL"
                lbl_color = "#00A86B" if is_sample_ok else "#FF0000"
                line_text = f"{i18n.t('run.resultado_idx', idx=idx+1)}: {m_val:.2f} cNm ({status_txt})"
            else:
                line_text = f"{i18n.t('run.resultado_idx_skipped', idx=idx+1)}"
                lbl_color = "gray40"
                
            lbl_line = ctk.CTkLabel(
                results_list_frame,
                text=line_text,
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=lbl_color
            )
            lbl_line.pack(anchor="w", pady=3)
            
        # Right action buttons
        btn_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e", padx=30, pady=15)
        
        btn_fg = "#FF0000" if overall_result == "FAIL" else "#00A86B"
        btn_hover = "#D32F2F" if overall_result == "FAIL" else "#008E5A"
        
        btn_save = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.save_return"),
            height=45,
            width=200,
            fg_color=btn_fg,
            hover_color=btn_hover,
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.save_and_finish
        )
        btn_save.pack(pady=5)
        
        btn_retry = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.retry"),
            height=45,
            width=200,
            fg_color="gray25",
            hover_color="gray35",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.retry_test
        )
        btn_retry.pack(pady=5)

    def poll_sensor(self):
        """Continually read current and peak values from the sensor."""
        if not self.is_active or not self.app.sensor:
            # Re-schedule next poll anyway, but skip processing
            self.after(50, self.poll_sensor)
            return
            
        current = self.app.sensor.read_torque()
        peak = self.app.sensor.get_peak()
        
        abs_current = abs(current)
        abs_peak = abs(peak)
        
        try:
            self.live_lbl.configure(text=f"{i18n.t('run.live')}: {abs_current:.2f} cNm")
            self.peak_lbl.configure(text=f"{i18n.t('run.peak')}: {abs_peak:.2f} cNm")
        except Exception:
            pass

        # Auto-capture logic
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
                
                # Snap back
                if abs_current < self.tracked_peak * 0.85 and (self.tracked_peak - abs_current >= 0.5):
                    self.auto_capture_state = "CAPTURED"
                    self.capture_sample(self.tracked_peak)
            elif self.auto_capture_state == "CAPTURED":
                if abs_current < reset_threshold:
                    self.auto_capture_state = "IDLE"
                    self.tracked_peak = 0.0
        
        self.after(50, self.poll_sensor)

    def trigger_simulated_torque(self):
        if hasattr(self.app.sensor, "start_torque_cycle"):
            self.app.sensor.start_torque_cycle(self.test_def.target_value)

    def reset_sensor_peak(self):
        if self.app.sensor:
            self.app.sensor.reset_peak()
            self.auto_capture_state = "IDLE"
            self.tracked_peak = 0.0
            self.trigger_simulated_torque()
            self.peak_lbl.configure(text=f"{i18n.t('run.peak')}: 0.00 cNm")

    def start_measurements(self):
        """Mock method for test suite compatibility."""
        self.show_measuring_phase()

    def capture_sample(self, val=None):
        # Allow programmatic test overrides (where val is passed) to bypass is_active check
        is_programmatic = (val is not None)
        if not is_programmatic and (not self.is_active or not self.app.sensor):
            return
            
        measured_val = val if val is not None else self.app.sensor.get_peak()
        abs_val = abs(measured_val)
        is_lh = getattr(self.driver, 'handedness', 'right') == 'left'
        signed_val = -abs_val if is_lh else abs_val
        
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
        
        # Add measurement to DB
        self.app.db.add_measurement(self.session_id, self.current_sample_idx, signed_val, result_str)
        
        # Show sample result screen
        self.show_sample_result_phase(abs_val, is_ok, programmatic=is_programmatic)

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
                
        # Since 1 bad sample stops the whole test, overall result is PASS only if all samples OK
        self.overall_result = "PASS" if ok_count == self.test_def.num_samples else "FAIL"
        
        if self.on_step_complete:
            self.save_and_finish()
        else:
            self.show_result_screen(self.overall_result, ok_count)

    def save_and_finish(self):
        """Finalize DB records and trigger completion callbacks."""
        self.is_active = False
        self.app.db.complete_test_session(self.session_id, self.overall_result)
        log_action(
            self.app.user_manager.current_user.username, 
            "COMPLETE_TEST_SESSION", 
            f"Session {self.session_id} ended with {self.overall_result}"
        )
        
        if self.on_step_complete:
            self.on_step_complete(self.overall_result, self.session_id)
        else:
            self.return_to_dashboard()

    def retry_test(self):
        """Discard current session and starts a new one."""
        self.is_active = False
        if self.session_id:
            self.app.db.complete_test_session(self.session_id, "ABORTED")
            log_action(
                self.app.user_manager.current_user.username, 
                "ABORT_TEST_SESSION", 
                f"Session {self.session_id} aborted by operator for retry"
            )
            
        self.current_sample_idx = 0
        self.measurements = []
        self.session_id = None
        
        self.show_instruction_phase()

    def abort_test(self):
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
