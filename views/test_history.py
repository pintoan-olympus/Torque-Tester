import customtkinter as ctk
from utils.logger import get_logger
from utils.helpers import format_datetime
from views.components import ScrollableTable
import i18n

logger = get_logger()

class TestHistoryView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Layout configure: 1 column, rows for header, filters, table
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=0) # Filters
        self.grid_rowconfigure(2, weight=1) # Table
        
        # 1. Header Row
        self.header_lbl = ctk.CTkLabel(self, text=i18n.t("hist.title").upper(), font=ctk.CTkFont(size=18, weight="bold"))
        self.header_lbl.grid(row=0, column=0, pady=(10, 15), padx=10, sticky="w")
        
        # 2. Filters Row
        self.filters_frame = ctk.CTkFrame(self, height=70, corner_radius=8, fg_color="gray15")
        self.filters_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Driver ID filter
        d_lbl = ctk.CTkLabel(self.filters_frame, text=f"{i18n.t('hist.col_driver')}:", font=ctk.CTkFont(size=11, weight="bold"))
        d_lbl.grid(row=0, column=0, padx=(15, 5), pady=15, sticky="e")
        self.driver_filter = ctk.CTkEntry(self.filters_frame, placeholder_text="e.g. DRV-001", width=120)
        self.driver_filter.grid(row=0, column=1, padx=5, pady=15)
        self.driver_filter.bind("<KeyRelease>", lambda e: self.load_history())
        
        # Workbench filter
        w_lbl = ctk.CTkLabel(self.filters_frame, text=f"{i18n.t('hist.col_bench')}:", font=ctk.CTkFont(size=11, weight="bold"))
        w_lbl.grid(row=0, column=2, padx=10, pady=15, sticky="e")
        self.workbench_filter = ctk.CTkEntry(self.filters_frame, placeholder_text="e.g. Bench A", width=120)
        self.workbench_filter.grid(row=0, column=3, padx=5, pady=15)
        self.workbench_filter.bind("<KeyRelease>", lambda e: self.load_history())
        
        # Result filter
        r_lbl = ctk.CTkLabel(self.filters_frame, text=f"{i18n.t('hist.col_res')}:", font=ctk.CTkFont(size=11, weight="bold"))
        r_lbl.grid(row=0, column=4, padx=10, pady=15, sticky="e")
        self.result_filter = ctk.CTkComboBox(
            self.filters_frame, 
            values=["All", "PASS", "FAIL", "ABORTED"],
            width=110,
            command=lambda choice: self.load_history()
        )
        self.result_filter.grid(row=0, column=5, padx=5, pady=15)
        
        # Reset Filters button
        reset_btn = ctk.CTkButton(
            self.filters_frame, 
            text=i18n.t("drv.cancel"), 
            width=70, 
            fg_color="gray30", 
            hover_color="gray40", 
            command=self.reset_filters
        )
        reset_btn.grid(row=0, column=6, padx=(15, 10), pady=15)
        
        # Export to CSV button
        export_btn = ctk.CTkButton(
            self.filters_frame, 
            text=i18n.t("hist.export"), 
            width=120, 
            fg_color="#1a7a3a", 
            hover_color="#145e2c", 
            command=self.export_history_to_csv
        )
        export_btn.grid(row=0, column=7, padx=(10, 15), pady=15)
        
        # 3. History Scrollable Table
        self.table = ScrollableTable(
            self,
            headers=[
                i18n.t("hist.col_driver"), 
                i18n.t("hist.col_bench"), 
                "Operator", 
                i18n.t("hist.col_test"), 
                i18n.t("hist.col_res"), 
                i18n.t("hist.col_date"), 
                i18n.t("hist.col_actions")
            ],
            column_weights=[2, 2, 2, 3, 2, 3, 2],
            fg_color="gray15",
            corner_radius=8
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Initial Load
        self.load_history()

    def reset_filters(self):
        self.driver_filter.delete(0, "end")
        self.workbench_filter.delete(0, "end")
        self.result_filter.set("All")
        self.load_history()

    def load_history(self):
        # Fetch filter inputs
        driver_q = self.driver_filter.get().strip()
        bench_q = self.workbench_filter.get().strip()
        res_q = self.result_filter.get()
        if res_q == "All":
            res_q = None
            
        self.table.clear()
        
        history_data = self.app.db.get_test_history(
            driver_id_str=driver_q,
            workbench=bench_q,
            result=res_q
        )
        
        for record in history_data:
            res = record["overall_result"]
            res_color = "green" if res == "PASS" else ("red" if res == "FAIL" else "orange")
            
            # Setup cell action for Details button click based on type
            cell_commands = {}
            if record["record_type"] == "battery":
                # For battery, show the list of steps in a custom popup
                cell_commands[6] = lambda rec=record: self.show_battery_details_popup(rec)
                display_name = f"🔋 {record['test_name']}"
            else:
                session_id = record["session_id"]
                cell_commands[6] = lambda sid=session_id: self.show_session_details_popup(sid)
                display_name = f"📋 {record['test_name']}"
            
            self.table.add_row(
                [
                    record["driver_id_str"],
                    record["workbench"],
                    record["operator_name"],
                    display_name,
                    res,
                    format_datetime(record["started_at"]),
                    i18n.t("hist.view_steps")
                ],
                text_color=res_color,
                cell_commands=cell_commands
            )

    def show_battery_details_popup(self, record):
        """Display window overlay listing steps of a battery session."""
        popup = ctk.CTkToplevel(self)
        popup.title(f"Battery Details - Session {record['session_id']}")
        popup.geometry("550x450")
        popup.minsize(500, 350)
        popup.transient(self.app)
        popup.grab_set()
        
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(1, weight=1)
        
        lbl = ctk.CTkLabel(
            popup, 
            text=f"BATTERY STEPS: {record['test_name'].upper()}", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=0, column=0, pady=15, padx=20, sticky="w")
        
        pop_table = ScrollableTable(
            popup,
            headers=["Sequence #", "Test Name", "Result", "Details"],
            column_weights=[1, 3, 2, 2],
            fg_color="gray15"
        )
        pop_table.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        
        steps = record.get("steps") or []
        for idx, step in enumerate(steps):
            r = step["overall_result"]
            c = "green" if r == "PASS" else ("red" if r == "FAIL" else "gray")
            
            step_sid = step["session_id"]
            cell_cmds = {
                3: lambda sid=step_sid: self.show_session_details_popup(sid)
            }
            
            pop_table.add_row(
                [f"#{idx + 1}", step["test_name"], r, i18n.t("hist.view_steps")],
                text_color=c,
                cell_commands=cell_cmds
            )

    def show_session_details_popup(self, session_id):
        """Display window overlay with step-by-step measurements for session."""
        measurements = self.app.db.get_measurements_for_session(session_id)
        
        # Create a small modal-like details window
        popup = ctk.CTkToplevel(self)
        popup.title(f"Test Details - Session {session_id}")
        popup.geometry("450x450")
        popup.minsize(400, 350)
        popup.transient(self.app)
        popup.grab_set()
        
        popup.grid_columnconfigure(0, weight=1)
        popup.grid_rowconfigure(1, weight=1)
        
        lbl = ctk.CTkLabel(
            popup, 
            text=f"MEASUREMENTS FOR TEST #{session_id}", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl.grid(row=0, column=0, pady=15, padx=20, sticky="w")
        
        pop_table = ScrollableTable(
            popup,
            headers=["Sample #", "Measured Value (cNm)", "Result Check"],
            column_weights=[1, 2, 2],
            fg_color="gray15"
        )
        pop_table.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 15))
        
        for m in measurements:
            r = m["result"]
            c = "green" if r == "OK" else "red"
            pop_table.add_row(
                [f"Sample {m['sample_number']}", f"{m['measured_value']:.2f}", r],
                text_color=c
            )

    def export_history_to_csv(self):
        from tkinter import filedialog, messagebox
        import csv
        
        driver_q = self.driver_filter.get().strip()
        bench_q = self.workbench_filter.get().strip()
        res_q = self.result_filter.get()
        if res_q == "All":
            res_q = None
            
        history_data = self.app.db.get_test_history(
            driver_id_str=driver_q,
            workbench=bench_q,
            result=res_q
        )
        
        if not history_data:
            messagebox.showinfo("Export History", "No test run history records found to export.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Export Test Run History to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="test_run_history_export.csv"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Torque Tester System - Test Run History Export"])
                writer.writerow([])
                writer.writerow([
                    "Session ID", 
                    "Driver ID", 
                    "Brand", 
                    "Model", 
                    "Workbench", 
                    "Operator", 
                    "Test / Battery Procedure", 
                    "Overall Result", 
                    "Date/Time"
                ])
                for r in history_data:
                    if r["record_type"] == "battery":
                        # Write parent battery row
                        writer.writerow([
                            r["session_id"],
                            r["driver_id_str"],
                            r["brand"] or "",
                            r["model"] or "",
                            r["workbench"],
                            r["operator_name"],
                            f"Bateria: {r['test_name']}",
                            r["overall_result"],
                            format_datetime(r["started_at"])
                        ])
                        # Write steps sequentially grouped right under it
                        for idx, step in enumerate(r.get("steps") or []):
                            writer.writerow([
                                f"Step {idx+1}",
                                "",
                                "",
                                "",
                                "",
                                "",
                                f"  ↳ {step['test_name']}",
                                step["overall_result"],
                                format_datetime(step["started_at"])
                            ])
                    else:
                        # Write single standalone test row
                        writer.writerow([
                            r["session_id"],
                            r["driver_id_str"],
                            r["brand"] or "",
                            r["model"] or "",
                            r["workbench"],
                            r["operator_name"],
                            f"Teste: {r['test_name']}",
                            r["overall_result"],
                            format_datetime(r["started_at"])
                        ])
            messagebox.showinfo("Export History", f"Successfully exported {len(history_data)} records to {file_path}")
            logger.info(f"Test run history successfully exported to CSV: {file_path}")
        except Exception as e:
            logger.error(f"Error exporting test run history to CSV: {e}")
            messagebox.showerror("Export History", f"Error exporting test run history to CSV: {e}")
