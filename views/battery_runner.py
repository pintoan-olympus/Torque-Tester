import customtkinter as ctk
from datetime import datetime
from utils.logger import get_logger, log_action
from views.test_runner import TestRunnerView
from views.components import ScrollableTable

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
            on_step_complete=self.on_step_complete
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

        # Build summary container
        summary_frame = ctk.CTkFrame(self, corner_radius=12, fg_color="gray15")
        summary_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        summary_frame.grid_columnconfigure(0, weight=1)
        summary_frame.grid_rowconfigure(2, weight=1)

        # 1. Header banner
        banner = ctk.CTkFrame(summary_frame, corner_radius=10)
        banner.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 15))
        
        if overall_result == "PASS":
            banner.configure(fg_color="green")
            title = ctk.CTkLabel(banner, text="🎉 BATTERY TEST PASSED", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
            title.pack(pady=(15, 5))
            sub = ctk.CTkLabel(banner, text=f"All {len(self.steps)} test procedures passed verification criteria successfully.", font=ctk.CTkFont(size=13), text_color="white")
            sub.pack(pady=(0, 15))
        else:
            banner.configure(fg_color="red4")
            title = ctk.CTkLabel(banner, text="❌ BATTERY TEST FAILED", font=ctk.CTkFont(size=22, weight="bold"), text_color="white")
            title.pack(pady=(15, 5))
            sub = ctk.CTkLabel(banner, text="One or more test procedures in the battery did not pass.", font=ctk.CTkFont(size=13), text_color="white")
            sub.pack(pady=(0, 5))
            
            warning_lbl = ctk.CTkLabel(
                banner, 
                text="⚠️ Report test result to supervisor. DO NOT USE THE DRIVER!",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="red"
            )
            warning_lbl.pack(pady=(5, 15))

        # 2. Results table list
        t_title = ctk.CTkLabel(summary_frame, text="TEST SEQUENCES STATUS SUMMARY", font=ctk.CTkFont(size=14, weight="bold"))
        t_title.grid(row=1, column=0, sticky="w", padx=25, pady=(10, 5))

        table = ScrollableTable(
            summary_frame,
            headers=["Sequence #", "Test Name", "Result"],
            column_weights=[1, 4, 2],
            fg_color="transparent"
        )
        table.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)

        for idx, item in enumerate(self.step_results):
            res = item["result"]
            if res == "PASS":
                color = "green"
                res_disp = "✅ PASS"
            elif res == "FAIL":
                color = "red"
                res_disp = "❌ FAIL"
            else:
                color = "gray60"
                res_disp = "➖ SKIPPED"
            table.add_row([f"{idx + 1}", item["name"], res_disp], text_color=color)

        # 3. Action button
        btn = ctk.CTkButton(
            summary_frame,
            text="Save & Return to Menu",
            height=45,
            fg_color="green" if overall_result == "PASS" else "red4",
            hover_color="darkgreen" if overall_result == "PASS" else "red3",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.return_to_dashboard
        )
        btn.grid(row=3, column=0, sticky="ew", padx=20, pady=20)

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
