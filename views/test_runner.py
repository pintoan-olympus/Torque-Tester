import customtkinter as ctk
import time
from datetime import datetime
from utils.logger import get_logger, log_action
from utils.helpers import check_tolerance, format_datetime
import i18n

logger = get_logger()

class DirectionAnimation(ctk.CTkCanvas):
    def __init__(self, master, width=160, height=160, **kwargs):
        # HMI measuring screen is dark (#151515), so match background
        super().__init__(master, width=width, height=height, bg="#151515", highlightthickness=0, **kwargs)
        self.width = width
        self.height = height
        self.angle = 0
        self.direction = "IDLE"  # "CW", "CCW", or "IDLE"
        self.draw_idle()
        self.animate()

    def set_direction(self, direction):
        if self.direction != direction:
            self.direction = direction
            if direction == "IDLE":
                self.draw_idle()

    def draw_idle(self):
        self.delete("all")
        cx, cy = self.width // 2, self.height // 2
        r = min(self.width, self.height) // 3
        # Draw a neutral gray circle in the center
        self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="gray40", width=3)
        self.create_text(cx, cy, text="IDLE", fill="gray60", font=("Arial", 14, "bold"))

    def animate(self):
        # We only redraw when active to prevent CPU load and GUI stuttering
        if self.direction != "IDLE":
            self.delete("all")
            cx, cy = self.width // 2, self.height // 2
            r = min(self.width, self.height) // 3
            
            # Spin angle
            if self.direction == "CW":
                self.angle = (self.angle + 12) % 360
                color = "#00A86B"  # Green
                text_dir = "CW +"
            else:  # CCW
                self.angle = (self.angle - 12) % 360
                color = "#FF9F00"  # Orange/yellow
                text_dir = "CCW -"

            # Draw a beautiful rotating arc and arrow
            self.create_oval(cx - r, cy - r, cx + r, cy + r, outline="gray20", width=2)
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=self.angle, extent=90, outline=color, width=6, style="arc")
            self.create_arc(cx - r, cy - r, cx + r, cy + r, start=self.angle + 180, extent=90, outline=color, width=6, style="arc")
            
            # Add bold direction text in center
            self.create_text(cx, cy, text=text_dir, fill=color, font=("Arial", 16, "bold"))

        # Re-schedule animation loop
        self.after(50, self.animate)


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
        self.container = ctk.CTkFrame(self, corner_radius=12, fg_color="gray95")
        self.container.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Start by showing Screen 1 (Start Screen)
        self.show_start_screen()

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

    def clear_container(self, bg_color="gray95"):
        """Clean all widgets from self.container and reset row/col weights."""
        for widget in self.container.winfo_children():
            widget.destroy()
        self.container.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=0)
        self.container.grid_columnconfigure((0, 1, 2), weight=0)
        self.container.configure(fg_color=bg_color)

    def show_start_screen(self):
        """Screen 1 — Start Screen (Neutral background, large Set Torque message)"""
        self.is_active = False
        self.clear_container(bg_color="gray95")
        
        # Grid weights for vertical centering
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure((0, 5), weight=2)
        self.container.grid_rowconfigure((1, 2, 3, 4), weight=1)
        
        # Large Title
        lbl_title = ctk.CTkLabel(
            self.container,
            text=i18n.t("run.torque_test").upper(),
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="gray15"
        )
        lbl_title.grid(row=1, column=0, pady=(20, 5))
        
        # Centered message: Set Torque to X
        target_val = self.test_def.target_value
        target_text = i18n.t("run.set_torque", target=f"{target_val:.2f}")
        lbl_target = ctk.CTkLabel(
            self.container,
            text=target_text,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="gray25"
        )
        lbl_target.grid(row=2, column=0, pady=10)
        
        # Large Primary Action Button
        btn_start = ctk.CTkButton(
            self.container,
            text=i18n.t("run.start_btn"),
            height=60,
            width=320,
            fg_color="#00A86B",
            hover_color="#008E5A",
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self.show_measuring_screen
        )
        btn_start.grid(row=3, column=0, pady=(20, 20))
        
        # Recent test results section
        recent_frame = ctk.CTkFrame(self.container, fg_color="gray90", corner_radius=8)
        recent_frame.grid(row=4, column=0, sticky="ew", padx=50, pady=(10, 20))
        recent_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Recent title
        lbl_recent_title = ctk.CTkLabel(
            recent_frame,
            text=i18n.t("run.recent_results").upper(),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray40"
        )
        lbl_recent_title.grid(row=0, column=0, columnspan=3, pady=(5, 5), padx=10, sticky="w")
        
        # Headers
        ctk.CTkLabel(recent_frame, text=i18n.t("run.date"), font=ctk.CTkFont(size=11, weight="bold"), text_color="gray50").grid(row=1, column=0, sticky="w", padx=15, pady=2)
        ctk.CTkLabel(recent_frame, text=i18n.t("run.bench"), font=ctk.CTkFont(size=11, weight="bold"), text_color="gray50").grid(row=1, column=1, sticky="w", padx=15, pady=2)
        ctk.CTkLabel(recent_frame, text=i18n.t("run.status"), font=ctk.CTkFont(size=11, weight="bold"), text_color="gray50").grid(row=1, column=2, sticky="w", padx=15, pady=2)
        
        # Load 3 recent results
        try:
            history = self.app.db.get_test_history()
            recent_runs = [h for h in history if h.get("workbench") == self.workbench][:3]
            if not recent_runs:
                recent_runs = history[:3]
                
            for idx, r in enumerate(recent_runs):
                row_idx = idx + 2
                res = r.get("overall_result", "ABORTED")
                res_color = "green" if res == "PASS" else ("red" if res == "FAIL" else "orange")
                
                ctk.CTkLabel(recent_frame, text=format_datetime(r.get("started_at")), font=ctk.CTkFont(size=11), text_color="gray20").grid(row=row_idx, column=0, sticky="w", padx=15, pady=1)
                ctk.CTkLabel(recent_frame, text=r.get("workbench"), font=ctk.CTkFont(size=11), text_color="gray20").grid(row=row_idx, column=1, sticky="w", padx=15, pady=1)
                ctk.CTkLabel(recent_frame, text=res, font=ctk.CTkFont(size=11, weight="bold"), text_color=res_color).grid(row=row_idx, column=2, sticky="w", padx=15, pady=1)
        except Exception as e:
            logger.error(f"Error loading recent results: {e}")

    def show_measuring_screen(self):
        """Screen 2 — Test Running (Dark background, live measurement & direction animation)"""
        self.clear_container(bg_color="#151515")
        self.is_active = True
        
        # Start DB Session if not already started
        if self.session_id is None:
            self.db_start_session()
            
        # Grid weights
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=0)  # Top stats/progress
        self.container.grid_rowconfigure(1, weight=1)  # Animated Canvas & limits
        self.container.grid_rowconfigure(2, weight=1)  # Value / Status
        self.container.grid_rowconfigure(3, weight=0)  # Capture / Reset / Abort
        
        # Top Stats Bar (Touch friendly, high visibility)
        top_bar = ctk.CTkFrame(self.container, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        top_bar.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Progress: Test X of Y
        prog_text = f"{i18n.t('run.test_n_of_m', n=self.step_number, m=self.total_steps)} | {i18n.t('run.sample_n_of_m', n=self.current_sample_idx + 1, total=self.test_def.num_samples)}"
        lbl_progress = ctk.CTkLabel(
            top_bar,
            text=prog_text.upper(),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="gray60"
        )
        lbl_progress.grid(row=0, column=0, sticky="w")
        
        # Tester & Direction Identification
                        # Handedness check
        is_lh = getattr(self.driver, 'handedness', 'right') == 'left'
        wrench_dir = "CCW -" if is_lh else "CW +"
        sensor_name = f"Sensor {self.test_def.default_tester_id or 'A'}"
        
        lbl_ident = ctk.CTkLabel(
            top_bar,
            text=f"{sensor_name} | {wrench_dir}",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="orange"
        )
        lbl_ident.grid(row=0, column=1)
        
        # Acceptable Limits Box
        low = self.test_def.target_value - self.test_def.tolerance_minus
        high = self.test_def.target_value + self.test_def.tolerance_plus
        lbl_limits = ctk.CTkLabel(
            top_bar,
            text=f"{i18n.t('run.limits').upper()}: {low:.2f} - {high:.2f} cNm",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="gray60"
        )
        lbl_limits.grid(row=0, column=2, sticky="e")
        
        # Center Row layout: Canvas (Left) and Range specification details (Right)
        center_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        center_frame.grid(row=1, column=0, sticky="nsew", padx=40, pady=5)
        center_frame.grid_columnconfigure((0, 1), weight=1)
        center_frame.grid_rowconfigure(0, weight=1)
        
        # Dynamic Direction indicator
        self.dir_anim = DirectionAnimation(center_frame)
        self.dir_anim.grid(row=0, column=0, padx=20, pady=10)
        
        # Status details card
        status_card = ctk.CTkFrame(center_frame, fg_color="gray10", corner_radius=10)
        status_card.grid(row=0, column=1, sticky="nsew", padx=20, pady=10)
        status_card.grid_columnconfigure(0, weight=1)
        status_card.grid_rowconfigure((0, 1), weight=1)
        
        self.meas_status_lbl = ctk.CTkLabel(
            status_card,
            text=i18n.t("run.measuring").upper(),
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="cyan"
        )
        self.meas_status_lbl.grid(row=0, column=0, sticky="s", pady=5)
        
        # Acceptable range badge
        lbl_spec_badge = ctk.CTkLabel(
            status_card,
            text=f"{i18n.t('run.target').upper()}: {self.test_def.target_value:.2f} cNm",
            fg_color="gray25",
            corner_radius=6,
            padx=15,
            pady=6,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="white"
        )
        lbl_spec_badge.grid(row=1, column=0, sticky="n", pady=5)
        
        # Real-time displays row
        displays_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        displays_frame.grid(row=2, column=0, sticky="ew", padx=40, pady=5)
        displays_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Real-time Torque
        self.live_lbl = ctk.CTkLabel(
            displays_frame,
            text=f"{i18n.t('run.live').upper()}: --- cNm",
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color="cyan"
        )
        self.live_lbl.grid(row=0, column=0, padx=20, pady=10)
        
        # Peak Torque
        self.peak_lbl = ctk.CTkLabel(
            displays_frame,
            text=f"{i18n.t('run.peak').upper()}: 0.00 cNm",
            font=ctk.CTkFont(size=44, weight="bold"),
            text_color="yellow"
        )
        self.peak_lbl.grid(row=0, column=1, padx=20, pady=10)
        
        # Controls Frame (Large centered button)
        controls_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        controls_frame.grid(row=3, column=0, sticky="ew", padx=40, pady=15)
        controls_frame.grid_columnconfigure(0, weight=1)
        
        btn_abort = ctk.CTkButton(
            controls_frame,
            text=i18n.t("run.abort", default="ABORT").upper(),
            height=55,
            width=260,
            fg_color="red4",
            hover_color="red3",
            text_color="white",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.abort_test
        )
        btn_abort.pack(pady=5, anchor="center")

        # Hidden Checkbox for auto-capture snapback state persistence
        self.auto_capture_cb = ctk.CTkCheckBox(self.container, variable=self.auto_capture_var)
        self.auto_capture_cb.grid_forget()

        # Start polling loop
        if not self.polling_started:
            self.polling_started = True
            self.poll_sensor()
            
        self.trigger_simulated_torque()

    def show_pass_screen(self, val, programmatic=False):
        """Screen 3 — PASS Result (Solid Green background bleed, large check icon)"""
        self.is_active = False
        self.clear_container(bg_color="#00A86B")
        
        # Grid weights
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure((0, 4), weight=1)
        self.container.grid_rowconfigure((1, 2, 3), weight=2)
        
        # Show "Test X of Y" progress
        prog_text = f"{i18n.t('run.test_n_of_m', n=self.step_number, m=self.total_steps)} | {i18n.t('run.sample_n_of_m', n=self.current_sample_idx, total=self.test_def.num_samples)}"
        lbl_prog = ctk.CTkLabel(
            self.container,
            text=prog_text.upper(),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        lbl_prog.grid(row=0, column=0, pady=10)
        
        # Large check mark and PASS
        lbl_status = ctk.CTkLabel(
            self.container,
            text="✓ PASS",
            font=ctk.CTkFont(size=64, weight="bold"),
            text_color="white"
        )
        lbl_status.grid(row=1, column=0, pady=5)
        
        # Measured torque value
        low = self.test_def.target_value - self.test_def.tolerance_minus
        high = self.test_def.target_value + self.test_def.tolerance_plus
        lbl_val = ctk.CTkLabel(
            self.container,
            text=f"{val:.2f} cNm  [{low:.2f} - {high:.2f}]",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="white"
        )
        lbl_val.grid(row=2, column=0, pady=5)
        
        # Message: Within Specification
        lbl_msg = ctk.CTkLabel(
            self.container,
            text=i18n.t("run.within_spec").upper(),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        lbl_msg.grid(row=3, column=0, pady=5)
        
        # Large primary action button: Next Test
        btn_next = ctk.CTkButton(
            self.container,
            text=i18n.t("run.next_test").upper(),
            height=60,
            width=280,
            fg_color="white",
            text_color="#00A86B",
            hover_color="gray90",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.auto_advance_flow
        )
        btn_next.grid(row=4, column=0, pady=30)
        
        # Timer or auto advance
        if programmatic:
            self.auto_advance_flow()
        else:
            self.after(1500, self.auto_advance_flow)

    def show_fail_screen(self, val):
        """Screen 4 — FAIL Result (Solid Red background bleed, large warning icon)"""
        self.is_active = False
        self.clear_container(bg_color="#FF0000")
        
        # Grid weights
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure((0, 4), weight=1)
        self.container.grid_rowconfigure((1, 2, 3), weight=2)
        
        # Show "Test X of Y" progress
        prog_text = f"{i18n.t('run.test_n_of_m', n=self.step_number, m=self.total_steps)} | {i18n.t('run.sample_n_of_m', n=self.current_sample_idx, total=self.test_def.num_samples)}"
        lbl_prog = ctk.CTkLabel(
            self.container,
            text=prog_text.upper(),
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        )
        lbl_prog.grid(row=0, column=0, pady=10)
        
        # Large warning mark and FAIL
        lbl_status = ctk.CTkLabel(
            self.container,
            text="⚠ FAIL",
            font=ctk.CTkFont(size=64, weight="bold"),
            text_color="white"
        )
        lbl_status.grid(row=1, column=0, pady=5)
        
        # Measured torque value
        low = self.test_def.target_value - self.test_def.tolerance_minus
        high = self.test_def.target_value + self.test_def.tolerance_plus
        lbl_val = ctk.CTkLabel(
            self.container,
            text=f"{val:.2f} cNm  [{low:.2f} - {high:.2f}]",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="white"
        )
        lbl_val.grid(row=2, column=0, pady=5)
        
        # Message: Out of Specification
        lbl_msg = ctk.CTkLabel(
            self.container,
            text=i18n.t("run.out_of_spec").upper(),
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        )
        lbl_msg.grid(row=3, column=0, pady=5)
        
        # Action Buttons frame
        btn_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        btn_frame.grid(row=4, column=0, pady=30)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        btn_repeat = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.repeat_test").upper(),
            height=60,
            width=220,
            fg_color="white",
            text_color="#FF0000",
            hover_color="gray90",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.repeat_failed_sample
        )
        btn_repeat.grid(row=0, column=0, padx=10)
        
        btn_continue = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.continue_summary").upper(),
            height=60,
            width=260,
            fg_color="gray15",
            text_color="white",
            hover_color="gray25",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.finish_test
        )
        btn_continue.grid(row=0, column=1, padx=10)

    def repeat_failed_sample(self):
        """Repeat current failed sample/step (removes last measurement entry)."""
        if self.measurements:
            self.measurements.pop()
            self.current_sample_idx -= 1
        self.show_measuring_screen()

    def show_final_summary_screen(self, overall_result, ok_count):
        """Screen 5 — Final Summary (Solid background bleed based on result)"""
        self.is_active = False
        bg_color = "#00A86B" if overall_result == "PASS" else "#FF0000"
        self.clear_container(bg_color=bg_color)
        
        # Grid layout
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=2)  # Overall Result Banner
        self.container.grid_rowconfigure(1, weight=3)  # Bottom white card (Logs list)
        
        # Top banner labels
        top_banner = ctk.CTkFrame(self.container, fg_color="transparent")
        top_banner.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        top_banner.grid_columnconfigure(0, weight=1)
        top_banner.grid_rowconfigure((0, 1, 2), weight=1)
        
        lbl_test = ctk.CTkLabel(
            top_banner,
            text=self.test_def.name.upper(),
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="white"
        )
        lbl_test.grid(row=0, column=0, sticky="s", pady=(10, 5))
        
        res_text = i18n.t("run.result_pass") if overall_result == "PASS" else i18n.t("run.result_fail")
        lbl_res = ctk.CTkLabel(
            top_banner,
            text=res_text,
            font=ctk.CTkFont(size=56, weight="bold"),
            text_color="white"
        )
        lbl_res.grid(row=1, column=0, sticky="ew", pady=5)
        
        info_text = f"({ok_count} / {self.test_def.num_samples} samples passed)"
        lbl_info = ctk.CTkLabel(
            top_banner,
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
        
        # Left side: Results logs list
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
            
        # Right side: Large HMI buttons
        btn_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e", padx=30, pady=15)
        
        btn_save = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.save_results", default="SAVE RESULTS").upper(),
            height=50,
            width=220,
            fg_color="#00A86B",
            hover_color="#008E5A",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.save_and_finish
        )
        btn_save.pack(pady=6)
        
        btn_retry = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.repeat_tests", default="REPEAT TESTS").upper(),
            height=50,
            width=220,
            fg_color="gray30",
            hover_color="gray40",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.retry_test
        )
        btn_retry.pack(pady=6)
        
        btn_abort = ctk.CTkButton(
            btn_frame,
            text=i18n.t("run.abort", default="ABORT").upper(),
            height=50,
            width=220,
            fg_color="#FF0000",
            hover_color="#D32F2F",
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.abort_test
        )
        btn_abort.pack(pady=6)

    def auto_advance_flow(self):
        """Check if all samples are done, or continue to instructions of next sample."""
        if self.current_sample_idx >= self.test_def.num_samples:
            self.finish_test()
        else:
            self.show_start_screen()

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
            self.live_lbl.configure(text=f"{i18n.t('run.live').upper()}: {abs_current:.2f} cNm")
            self.peak_lbl.configure(text=f"{i18n.t('run.peak').upper()}: {abs_peak:.2f} cNm")
        except Exception:
            pass

        # Set rotation direction animation states based on reading polarity
        if current > 0.15:
            self.dir_anim.set_direction("CW")
        elif current < -0.15:
            self.dir_anim.set_direction("CCW")
        else:
            self.dir_anim.set_direction("IDLE")

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
            self.peak_lbl.configure(text=f"{i18n.t('run.peak').upper()}: 0.00 cNm")

    def start_measurements(self):
        """Mock method for test suite compatibility."""
        self.show_measuring_screen()

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
        
        # Show PASS/FAIL HMI result screen
        if is_ok:
            self.show_pass_screen(abs_val, programmatic=is_programmatic)
        else:
            self.show_fail_screen(abs_val)

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
            # For battery flow, save and trigger completion immediately
            self.save_and_finish()
        else:
            # Standalone mode: show HMI Summary screen
            self.show_final_summary_screen(self.overall_result, ok_count)

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
        
        self.show_start_screen()

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
