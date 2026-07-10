import customtkinter as ctk
from datetime import datetime
from utils.logger import get_logger, log_action
from views.test_runner import TestRunnerView
from views.components import ScrollableTable
import i18n

logger = get_logger()

class BatteryRunnerView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Verify setup state
        if not self.app.selected_driver or not self.app.selected_battery or not self.app.selected_workbench:
            self.show_error_redirect()
            return
            
        self.driver = self.app.selected_driver
        self.battery = self.app.selected_battery
        self.workbench = self.app.selected_workbench
        self.steps = self.app.battery_items
        
        if not self.steps:
            self.show_error_redirect("Selected battery has no test steps configured.")
            return

        self.current_step = 0
        self.step_results = [] # list of dicts: {"name": str, "result": str}
        self.battery_session_id = None
        self.active_runner = None

        # Start battery session
        self.db_start_battery_session()

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Run first step
        self.run_current_step()

    def show_error_redirect(self, message="Incomplete Session Parameters!"):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        card = ctk.CTkFrame(self, width=400, height=200, corner_radius=10, fg_color="gray15")
        card.grid(row=0, column=0)
        
        lbl = ctk.CTkLabel(card, text=message, font=ctk.CTkFont(size=15, weight="bold"), text_color="red")
        lbl.pack(pady=30, padx=20)
        
        from views.dashboard import DashboardView
        btn = ctk.CTkButton(card, text="Go to Dashboard", command=lambda: self.app.show_view(DashboardView))
        btn.pack(pady=10)

    def db_start_battery_session(self):
        self.battery_session_id = self.app.db.start_battery_session(
            battery_id=self.battery.id,
            driver_id=self.driver.id,
            workbench=self.workbench,
            operator_id=self.app.user_manager.current_user.id
        )
        log_action(
            self.app.user_manager.current_user.username, 
            "START_BATTERY_SESSION", 
            f"Battery session {self.battery_session_id} started for battery '{self.battery.name}'"
        )

    def run_current_step(self):
        # Destroy active runner if exists
        if self.active_runner:
            self.active_runner.destroy()
            self.active_runner = None

        # Get current step definition
        battery_item = self.steps[self.current_step]
        self.app.selected_test_def = battery_item.test_def

        # Reset active sensor peak values
        if self.app.sensor:
            self.app.sensor.reset_peak()

        # Instantiate the customized TestRunnerView
        self.active_runner = TestRunnerView(
            master=self,
            app=self.app,
            step_number=self.current_step + 1,
            total_steps=len(self.steps),
            on_step_complete=self.on_step_complete,
            battery_session_id=self.battery_session_id
        )
        self.active_runner.grid(row=0, column=0, sticky="nsew")

    def on_step_complete(self, result, session_id):
        """Callback received from individual steps."""
        test_name = self.steps[self.current_step].test_def.name
        
        if result == "ABORTED":
            # Abort the entire battery session
            if self.battery_session_id:
                self.app.db.complete_battery_session(self.battery_session_id, "ABORTED")
                log_action(
                    self.app.user_manager.current_user.username, 
                    "ABORT_BATTERY_SESSION", 
                    f"Battery session {self.battery_session_id} aborted by operator during step '{test_name}'"
                )
            self.return_to_dashboard()
            return

        # Record step result
        self.step_results.append({
            "name": test_name,
            "result": result
        })

        if result == "FAIL":
            # Skip the remaining steps
            for i in range(self.current_step + 1, len(self.steps)):
                self.step_results.append({
                    "name": self.steps[i].test_def.name,
                    "result": "SKIP"
                })
            
            # Complete battery session with FAIL
            if self.battery_session_id:
                self.app.db.complete_battery_session(self.battery_session_id, "FAIL")
                log_action(
                    self.app.user_manager.current_user.username, 
                    "COMPLETE_BATTERY_SESSION", 
                    f"Battery session {self.battery_session_id} completed with result: FAIL"
                )
            
            self.show_summary_screen(overall_result="FAIL")
        
        elif result == "PASS":
            self.current_step += 1
            if self.current_step >= len(self.steps):
                # All steps completed successfully!
                if self.battery_session_id:
                    self.app.db.complete_battery_session(self.battery_session_id, "PASS")
                    log_action(
                        self.app.user_manager.current_user.username, 
                        "COMPLETE_BATTERY_SESSION", 
                        f"Battery session {self.battery_session_id} completed with result: PASS"
                    )
                self.show_summary_screen(overall_result="PASS")
            else:
                # Load next test in the battery sequence
                self.run_current_step()

    def show_summary_screen(self, overall_result):
        # Destroy active runner
        if self.active_runner:
            self.active_runner.destroy()
            self.active_runner = None

        # Determine background color based on overall result
        bg_banner_color = "#FF0000" if overall_result == "FAIL" else "#00A86B"

        # Build summary container frame with banner color as background
        summary_frame = ctk.CTkFrame(self, corner_radius=12, fg_color=bg_banner_color)
        summary_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        summary_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_rowconfigure(0, weight=3) # banner area
        summary_frame.grid_rowconfigure(1, weight=2) # bottom white card area

        # 1. TOP BANNER LABELS (gridded directly in summary_frame row 0)
        top_banner_content = ctk.CTkFrame(summary_frame, fg_color="transparent")
        top_banner_content.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        top_banner_content.grid_columnconfigure(0, weight=1)
        top_banner_content.grid_rowconfigure((0, 1, 2), weight=1)

        # Step Text (e.g. Test 3 of 3 / Teste 3 de 3)
        if overall_result == "FAIL":
            failed_step_idx = next((i for i, r in enumerate(self.step_results) if r["result"] == "FAIL"), 0)
            step_text = i18n.t("run.teste_n_of_m", n=failed_step_idx + 1, m=len(self.steps))
        else:
            step_text = i18n.t("run.battery_completed", n=len(self.steps), m=len(self.steps))

        lbl_step = ctk.CTkLabel(
            top_banner_content,
            text=step_text,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="white"
        )
        lbl_step.grid(row=0, column=0, pady=(20, 5), sticky="s")

        # Result Text (PASS/FAIL)
        lbl_result = ctk.CTkLabel(
            top_banner_content,
            text=overall_result,
            font=ctk.CTkFont(size=54, weight="bold"),
            text_color="white"
        )
        lbl_result.grid(row=1, column=0, pady=5, sticky="ew")

        # Supervisor Warning or Success Information
        if overall_result == "FAIL":
            info_text = i18n.t("run.battery_fail_warning")
        else:
            info_text = i18n.t("run.battery_success")

        lbl_info = ctk.CTkLabel(
            top_banner_content,
            text=info_text,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        lbl_info.grid(row=2, column=0, pady=(5, 20), sticky="n")

        # 2. BOTTOM DETAILS AREA (white card)
        bottom_area = ctk.CTkFrame(summary_frame, corner_radius=8, fg_color="white")
        bottom_area.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        bottom_area.grid_columnconfigure(0, weight=2)
        bottom_area.grid_columnconfigure(1, weight=1)
        bottom_area.grid_rowconfigure(0, weight=1)

        # Left side: Results list
        results_list_frame = ctk.CTkFrame(bottom_area, fg_color="transparent")
        results_list_frame.grid(row=0, column=0, sticky="nsw", padx=30, pady=15)

        for idx, item in enumerate(self.step_results):
            res = item["result"]
            if res == "PASS":
                color = "#00A86B"
                res_line = f"{i18n.t('run.resultado_idx', idx=idx+1)}"
            elif res == "FAIL":
                color = "#FF0000"
                res_line = f"{i18n.t('run.resultado_idx', idx=idx+1)}"
            else:
                color = "gray40"
                res_line = f"{i18n.t('run.resultado_idx_skipped', idx=idx+1)}"

            lbl_res = ctk.CTkLabel(
                results_list_frame,
                text=res_line,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=color
            )
            lbl_res.pack(anchor="w", pady=4)

        # Right side: Action Button (Save & Return to Menu)
        btn_fg = "#FF0000" if overall_result == "FAIL" else "#00A86B"
        btn_hover = "#D32F2F" if overall_result == "FAIL" else "#008E5A"

        btn_save = ctk.CTkButton(
            bottom_area,
            text=i18n.t("run.save_return"),
            height=45,
            width=200,
            fg_color=btn_fg,
            hover_color=btn_hover,
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.return_to_dashboard
        )
        btn_save.grid(row=0, column=1, sticky="e", padx=30, pady=15)

    def return_to_dashboard(self):
        self.app.selected_driver = None
        self.app.selected_test_def = None
        self.app.selected_battery = None
        self.app.battery_items = []
        
        from views.dashboard import DashboardView
        self.app.show_view(DashboardView)

    def destroy(self):
        if self.active_runner:
            self.active_runner.destroy()
        super().destroy()
