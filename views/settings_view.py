import customtkinter as ctk
import os
import config
import json
from utils.logger import get_logger, log_action
from sensor.serial_comm import TorqueSensorSerial

logger = get_logger()


class SettingsView(ctk.CTkFrame):
    """Settings view: tabbed hardware config (Tester A/B) on left, logs + data import/export on right."""

    # ─────────────────────────────── helpers defined FIRST ────────────────────
    def toggle_simulator_fields(self):
        """Grey out COM parameters when simulation mode is active."""
        tester_count = self.app.hw_config.get_setting("tester_count", 2)
        for idx in range(tester_count):
            if idx < len(self.sim_vars) and idx < len(self.port_combos):
                state = "disabled" if self.sim_vars[idx].get() else self.state_ctrl
                for w in (self.port_combos[idx], self.baud_combos[idx],
                          self.databits_combos[idx], self.parity_combos[idx], self.stopbits_combos[idx]):
                    w.configure(state=state)

    def test_connection_by_idx(self, idx: int):
        """Show the status of a specific Tester."""
        if idx >= len(self.sim_vars) or idx >= len(self.conn_status_lbls):
            return
            
        letter = chr(65 + idx)
        if self.sim_vars[idx].get():
            self.conn_status_lbls[idx].configure(
                text="Simulation mode active – no physical port needed.", text_color="cyan")
            return

        sensor = self.app.sensors[idx] if idx < len(self.app.sensors) else None
        if sensor and sensor.is_connected():
            port = getattr(sensor, "port", self.port_combos[idx].get())
            self.conn_status_lbls[idx].configure(
                text=f"✔ Sensor CONNECTED on {port}", text_color="green")
        else:
            port = self.port_combos[idx].get()
            self.conn_status_lbls[idx].configure(
                text=f"✘ Sensor OFFLINE – not connected to {port}", text_color="red")

    def test_connection_a(self):
        self.test_connection_by_idx(0)

    def test_connection_b(self):
        self.test_connection_by_idx(1)

    def save_settings_by_idx(self, idx: int):
        """Validate, persist settings to DB, then reconnect the specific Tester."""
        if idx >= len(self.sim_vars) or idx >= len(self.conn_status_lbls):
            return
            
        letter = chr(65 + idx)
        suffix = "" if idx == 0 else (f"_b" if idx == 1 else f"_{chr(97 + idx)}")
        
        sim_mode = self.sim_vars[idx].get()
        port = self.port_combos[idx].get()
        tester_model = self.model_combos[idx].get()

        try:
            baud = int(self.baud_combos[idx].get())
            bytesize = int(self.databits_combos[idx].get())
            p_combo = self.parity_combos[idx].get()
            parity = "N" if "N" in p_combo else ("E" if "E" in p_combo else "O")
            stopbits = float(self.stopbits_combos[idx].get())
            if stopbits.is_integer():
                stopbits = int(stopbits)
        except ValueError:
            self.conn_status_lbls[idx].configure(text="Save Failed: formatting errors.", text_color="red")
            return

        self.app.hw_config.set_setting(f"simulator_mode{suffix}", sim_mode)
        self.app.hw_config.set_setting(f"port{suffix}", port)
        self.app.hw_config.set_setting(f"baudrate{suffix}", baud)
        self.app.hw_config.set_setting(f"bytesize{suffix}", bytesize)
        self.app.hw_config.set_setting(f"parity{suffix}", parity)
        self.app.hw_config.set_setting(f"stopbits{suffix}", stopbits)
        self.app.hw_config.set_setting(f"tester_model{suffix}", tester_model)

        if tester_model == "Custom…":
            model_name = self.custom_name_entries[idx].get().strip() or f"Custom Tester {letter}"
            try:
                t_min = float(self.custom_min_entries[idx].get().strip() or 0.0)
                t_max = float(self.custom_max_entries[idx].get().strip() or 50.0)
            except ValueError:
                self.conn_status_lbls[idx].configure(text="Save Failed: Custom torque limits must be numeric.", text_color="red")
                return
            serial_pat = self.custom_pattern_entries[idx].get().strip() or r"([+-]?\d+\.\d+)\s*Nm"
            
            self.app.hw_config.set_setting(f"custom_model_name{suffix}", model_name)
            self.app.hw_config.set_setting(f"custom_torque_min{suffix}", t_min)
            self.app.hw_config.set_setting(f"custom_torque_max{suffix}", t_max)
            self.app.hw_config.set_setting(f"custom_serial_pattern{suffix}", serial_pat)

        log_action(self.app.user_manager.current_user.username,
                   f"SAVE_HARDWARE_SETTINGS_{letter}", f"Sim={sim_mode}, Port={port}, Model={tester_model}")
        self.conn_status_lbls[idx].configure(text=f"Settings saved. Reconnecting Tester {letter}…", text_color="orange")
        self.update_idletasks()

        self.app.reconnect_sensor_by_idx(idx)
        self.refresh_logs()
        self.conn_status_lbls[idx].configure(text=f"Tester {letter} settings applied and saved successfully.", text_color="green")

    def save_settings_a(self):
        self.save_settings_by_idx(0)

    def save_settings_b(self):
        self.save_settings_by_idx(1)

    def refresh_logs(self):
        """Read only the last ~16 KB tail of the log file to avoid freezing on large files."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        log_path = config.LOG_PATH
        if os.path.exists(log_path):
            try:
                tail_bytes = 16 * 1024  # 16 KB tail
                with open(log_path, "rb") as f:
                    f.seek(0, 2)
                    file_size = f.tell()
                    f.seek(max(0, file_size - tail_bytes))
                    raw = f.read()
                text = raw.decode("utf-8", errors="ignore")
                # Drop partial first line if we seeked mid-file
                if file_size > tail_bytes:
                    first_nl = text.find("\n")
                    if first_nl >= 0:
                        text = text[first_nl + 1:]
                # Filter out raw Serial RX debug lines to keep the log readable
                lines = [ln for ln in text.splitlines(keepends=True)
                         if "Serial RX:" not in ln]
                self.log_textbox.insert("1.0", "".join(lines))
            except Exception as e:
                self.log_textbox.insert("1.0", f"Error reading log file: {e}")
        else:
            self.log_textbox.insert("1.0", "No log file found.")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def poll_sensor(self):
        """150 ms polling loop – updates the live preview panels for all active testers."""
        if not self.is_active:
            return
        
        tester_count = self.app.hw_config.get_setting("tester_count", 2)
        for idx in range(tester_count):
            if idx >= len(self.live_status_vals):
                continue
            try:
                sensor = self.app.sensors[idx] if idx < len(self.app.sensors) else None
                if sensor and sensor.is_connected():
                    current = sensor.read_torque()
                    peak = sensor.get_peak()
                    self.live_torque_vals[idx].configure(text=f"{current:.2f} cNm", text_color="white")
                    self.live_peak_vals[idx].configure(text=f"{peak:.2f} cNm", text_color="#ff9f0a")
                    self.live_status_vals[idx].configure(text="ONLINE", text_color="#2ec4b6")

                    if hasattr(sensor, 'get_last_raw_frame'):
                        raw = sensor.get_last_raw_frame()
                        if raw:
                            self.raw_textboxes[idx].configure(state="normal")
                            self.raw_textboxes[idx].delete("1.0", "end")
                            self.raw_textboxes[idx].insert("end", raw)
                            self.raw_textboxes[idx].configure(state="disabled")
                else:
                    self.live_torque_vals[idx].configure(text="– – – cNm", text_color="gray50")
                    self.live_peak_vals[idx].configure(text="– – – cNm", text_color="gray50")
                    self.live_status_vals[idx].configure(text="OFFLINE", text_color="red")
                    self.raw_textboxes[idx].configure(state="normal")
                    self.raw_textboxes[idx].delete("1.0", "end")
                    self.raw_textboxes[idx].insert("end", "(no data – sensor offline)")
                    self.raw_textboxes[idx].configure(state="disabled")
            except Exception:
                pass

        self.after(150, self.poll_sensor)

    def reset_sensor_peak_by_idx(self, idx):
        if idx < len(self.app.sensors) and self.app.sensors[idx] and self.app.sensors[idx].is_connected():
            self.app.sensors[idx].reset_peak()

    def reset_sensor_peak_a(self):
        self.reset_sensor_peak_by_idx(0)

    def reset_sensor_peak_b(self):
        self.reset_sensor_peak_by_idx(1)

    # ── Database Import / Export ──────────────────────────────────────────────
    def export_drivers(self):
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="Export Drivers Database to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="torque_drivers_backup.csv"
        )
        if not file_path:
            return
        if self.app.db.export_table_to_csv("torque_drivers", file_path):
            self.import_status_lbl.configure(text=f"Drivers exported successfully to {os.path.basename(file_path)}", text_color="green")
            log_action(self.app.user_manager.current_user.username, "EXPORT_DRIVERS", file_path)
        else:
            self.import_status_lbl.configure(text="Failed to export drivers database.", text_color="red")

    def export_test_defs(self):
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            title="Export Test Procedures to CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="test_procedures_backup.csv"
        )
        if not file_path:
            return
        if self.app.db.export_table_to_csv("test_definitions", file_path):
            self.import_status_lbl.configure(text=f"Procedures exported successfully to {os.path.basename(file_path)}", text_color="green")
            log_action(self.app.user_manager.current_user.username, "EXPORT_TEST_TEMPLATES", file_path)
        else:
            self.import_status_lbl.configure(text="Failed to export test procedures database.", text_color="red")

    def import_drivers(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Drivers CSV to Import",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return
        stats = self.app.db.import_table_from_csv("torque_drivers", file_path)
        msg = f"Drivers Import: {stats['added']} added, {stats['updated']} updated, {stats['failed']} failed."
        self.import_status_lbl.configure(text=msg, text_color="green" if stats["failed"] == 0 else "orange")
        log_action(self.app.user_manager.current_user.username, "IMPORT_DRIVERS", f"File: {os.path.basename(file_path)}, {msg}")

    def import_test_defs(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Test Procedures CSV to Import",
            filetypes=[("CSV files", "*.csv")]
        )
        if not file_path:
            return
        stats = self.app.db.import_table_from_csv("test_definitions", file_path)
        msg = f"Procedures Import: {stats['added']} added, {stats['updated']} updated, {stats['failed']} failed."
        self.import_status_lbl.configure(text=msg, text_color="green" if stats["failed"] == 0 else "orange")
        log_action(self.app.user_manager.current_user.username, "IMPORT_TEST_TEMPLATES", f"File: {os.path.basename(file_path)}, {msg}")

    def reset_all_history(self):
        from tkinter import filedialog, messagebox
        
        # Confirm action first
        confirm = messagebox.askyesno(
            "Confirm Database Reset",
            "WARNING: This action will permanently delete ALL test sessions and measurements.\n\n"
            "You MUST export the database to a CSV backup file first.\n"
            "Do you want to proceed with exporting and resetting?"
        )
        if not confirm:
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Choose CSV Backup Location",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="test_records_history_backup.csv"
        )
        if not file_path:
            return
            
        success, msg = self.app.db.reset_all_test_data(file_path)
        if success:
            self.import_status_lbl.configure(text=msg, text_color="green")
            log_action(self.app.user_manager.current_user.username, "RESET_ALL_TEST_DATA", file_path)
            messagebox.showinfo("Reset Successful", msg)
        else:
            self.import_status_lbl.configure(text=f"Reset Failed: {msg}", text_color="red")
            messagebox.showerror("Reset Failed", f"An error occurred: {msg}")

    def destroy(self):
        """Stop the polling loop before the frame is destroyed."""
        self.is_active = False
        super().destroy()

    def on_model_changed(self, idx: int, choice: str):
        if idx < len(self.custom_frame_widgets):
            custom_frame = self.custom_frame_widgets[idx]
            if choice == "Custom…":
                custom_frame.pack(fill="x", padx=10, pady=5)
            else:
                custom_frame.pack_forget()

    def on_tab_changed(self):
        selected = self.tabview_left.get()
        if selected == "+":
            self.add_new_tester_tab()

    def add_new_tester_tab(self):
        count = self.app.hw_config.get_setting("tester_count", 2)
        if count >= 8:
            return
            
        count += 1
        self.app.hw_config.set_setting("tester_count", count)
        suffix = f"_{chr(97 + count - 1)}"
        
        self.app.hw_config.set_setting(f"port{suffix}", f"COM{count}")
        self.app.hw_config.set_setting(f"baudrate{suffix}", 9600)
        self.app.hw_config.set_setting(f"bytesize{suffix}", 8)
        self.app.hw_config.set_setting(f"parity{suffix}", "N")
        self.app.hw_config.set_setting(f"stopbits{suffix}", 1)
        self.app.hw_config.set_setting(f"timeout{suffix}", 1.0)
        self.app.hw_config.set_setting(f"simulator_mode{suffix}", True)
        self.app.hw_config.set_setting(f"tester_model{suffix}", "ng-TTS50-xu")
        
        log_action(self.app.user_manager.current_user.username, "ADD_TESTER_SLOT", f"Count: {count}")
        self.app.reconnect_sensor()
        self.app.show_view(SettingsView)

    def delete_tester_slot(self, idx: int):
        from tkinter import messagebox
        letter = chr(65 + idx)
        confirm = messagebox.askyesno(
            "Confirm Delete Tester",
            f"Are you sure you want to delete Tester {letter}?\n\nThis will remove its configuration settings."
        )
        if not confirm:
            return
            
        # Disconnect the sensor
        if idx < len(self.app.sensors) and self.app.sensors[idx]:
            try:
                self.app.sensors[idx].disconnect()
            except Exception:
                pass
            self.app.sensors.pop(idx)
            
        # Clean up settings from DB
        suffix = f"_{chr(97 + idx)}"
        self.app.hw_config.delete_settings_for_tester(suffix)
        
        # Decrement count
        count = self.app.hw_config.get_setting("tester_count", 2)
        if count > 2:
            self.app.hw_config.set_setting("tester_count", count - 1)
            
        log_action(self.app.user_manager.current_user.username, "DELETE_TESTER_SLOT", f"Index: {idx}, Count: {count-1}")
        self.app.reconnect_sensor()
        self.app.show_view(SettingsView)

    # ─────────────────────────────── constructor ──────────────────────────────
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.is_active = False

        # Permission level
        self.is_admin = self.app.user_manager.has_access(config.ACCESS_ADMIN)
        self.state_ctrl = "normal" if self.is_admin else "disabled"

        # 2-column layout
        self.grid_columnconfigure(0, weight=1, uniform="cols")
        self.grid_columnconfigure(1, weight=1, uniform="cols")
        self.grid_rowconfigure(0, weight=1)

        # Cache settings
        self.settings_cache = self.app.hw_config.get_all_settings()

        # ── LEFT PANEL: Tester config (Tabbed) ─────────────────────────────────
        controls_outer = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        controls_outer.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        controls_outer.grid_columnconfigure(0, weight=1)
        controls_outer.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            controls_outer,
            text="HARDWARE CONFIGURATION",
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, pady=(14, 4), padx=18, sticky="w")

        tester_count = self.settings_cache.get("tester_count", 2)
        
        self.sim_vars = []
        self.port_combos = []
        self.baud_combos = []
        self.databits_combos = []
        self.parity_combos = []
        self.stopbits_combos = []
        self.model_combos = []
        self.conn_status_lbls = []
        self.live_status_vals = []
        self.live_torque_vals = []
        self.live_peak_vals = []
        self.raw_textboxes = []
        
        self.custom_frame_widgets = []
        self.custom_name_entries = []
        self.custom_min_entries = []
        self.custom_max_entries = []
        self.custom_pattern_entries = []

        self.tabview_left = ctk.CTkTabview(controls_outer, fg_color="transparent", command=self.on_tab_changed)
        self.tabview_left.grid(row=1, column=0, sticky="nsew", padx=6, pady=4)
        
        for idx in range(tester_count):
            letter = chr(65 + idx)
            tab_name = f"Tester {letter}"
            tab = self.tabview_left.add(tab_name)
            tab.grid_columnconfigure(0, weight=1)
            
            scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
            scroll.grid(row=0, column=0, sticky="nsew")
            scroll.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
            
            suffix = "" if idx == 0 else (f"_b" if idx == 1 else f"_{chr(97 + idx)}")
            sim_mode_val = self.settings_cache.get(f"simulator_mode{suffix}", True)
            sim_var = ctk.BooleanVar(value=sim_mode_val)
            self.sim_vars.append(sim_var)
            
            ctk.CTkCheckBox(
                scroll, text="Enable Sensor Simulation (Simulator Mode)",
                variable=sim_var, state=self.state_ctrl,
                command=self.toggle_simulator_fields
            ).pack(pady=10, padx=15, anchor="w")
            
            comm_frame = ctk.CTkFrame(scroll, fg_color="gray12", corner_radius=6)
            comm_frame.pack(fill="x", padx=10, pady=5)
            comm_frame.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(comm_frame, text="Serial Port:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, padx=14, pady=5, sticky="w")
            available_ports = TorqueSensorSerial.list_available_ports() or ["COM1", "COM2", "COM3", "COM4"]
            current_port = self.settings_cache.get(f"port{suffix}", f"COM{idx+1}")
            if current_port not in available_ports:
                available_ports.append(current_port)
            port_combo = ctk.CTkComboBox(comm_frame, values=available_ports, state=self.state_ctrl)
            port_combo.set(current_port)
            port_combo.grid(row=0, column=1, padx=14, pady=5, sticky="ew")
            self.port_combos.append(port_combo)
            
            ctk.CTkLabel(comm_frame, text="Baud Rate:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=1, column=0, padx=14, pady=5, sticky="w")
            baud_combo = ctk.CTkComboBox(comm_frame, state=self.state_ctrl, values=["4800", "9600", "19200", "38400", "57600", "115200"])
            baud_combo.set(str(self.settings_cache.get(f"baudrate{suffix}", 9600)))
            baud_combo.grid(row=1, column=1, padx=14, pady=5, sticky="ew")
            self.baud_combos.append(baud_combo)
            
            ctk.CTkLabel(comm_frame, text="Data Bits:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=2, column=0, padx=14, pady=5, sticky="w")
            databits_combo = ctk.CTkComboBox(comm_frame, values=["7", "8"], state=self.state_ctrl)
            databits_combo.set(str(self.settings_cache.get(f"bytesize{suffix}", 8)))
            databits_combo.grid(row=2, column=1, padx=14, pady=5, sticky="ew")
            self.databits_combos.append(databits_combo)
            
            ctk.CTkLabel(comm_frame, text="Parity Check:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=3, column=0, padx=14, pady=5, sticky="w")
            parity_combo = ctk.CTkComboBox(comm_frame, state=self.state_ctrl, values=["N (None)", "E (Even)", "O (Odd)"])
            p_val = self.settings_cache.get(f"parity{suffix}", "N")
            parity_combo.set("N (None)" if p_val == "N" else ("E (Even)" if p_val == "E" else "O (Odd)"))
            parity_combo.grid(row=3, column=1, padx=14, pady=5, sticky="ew")
            self.parity_combos.append(parity_combo)
            
            ctk.CTkLabel(comm_frame, text="Stop Bits:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=4, column=0, padx=14, pady=5, sticky="w")
            stopbits_combo = ctk.CTkComboBox(comm_frame, values=["1", "1.5", "2"], state=self.state_ctrl)
            stopbits_combo.set(str(self.settings_cache.get(f"stopbits{suffix}", 1)))
            stopbits_combo.grid(row=4, column=1, padx=14, pady=5, sticky="ew")
            self.stopbits_combos.append(stopbits_combo)
            
            ctk.CTkLabel(comm_frame, text="Tester Model:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=5, column=0, padx=14, pady=5, sticky="w")
            model_combo = ctk.CTkComboBox(comm_frame, values=["ng-TTS50-xu", "ng-TTS500-xu", "Custom…"], state=self.state_ctrl,
                                         command=lambda choice, i=idx: self.on_model_changed(i, choice))
            current_model = self.settings_cache.get(f"tester_model{suffix}", "ng-TTS50-xu")
            model_combo.set(current_model)
            model_combo.grid(row=5, column=1, padx=14, pady=5, sticky="ew")
            self.model_combos.append(model_combo)
            
            custom_frame = ctk.CTkFrame(scroll, fg_color="gray12", corner_radius=6)
            custom_frame.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(custom_frame, text="Model Label Name:", font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=0, padx=14, pady=4, sticky="w")
            name_entry = ctk.CTkEntry(custom_frame, placeholder_text="e.g. My Sensor A")
            name_entry.insert(0, self.settings_cache.get(f"custom_model_name{suffix}", f"Custom Tester {letter}"))
            name_entry.grid(row=0, column=1, padx=14, pady=4, sticky="ew")
            self.custom_name_entries.append(name_entry)
            
            ctk.CTkLabel(custom_frame, text="Min Torque (cNm):", font=ctk.CTkFont(size=10, weight="bold")).grid(row=1, column=0, padx=14, pady=4, sticky="w")
            min_entry = ctk.CTkEntry(custom_frame, placeholder_text="e.g. 0.0")
            min_entry.insert(0, str(self.settings_cache.get(f"custom_torque_min{suffix}", 0.0)))
            min_entry.grid(row=1, column=1, padx=14, pady=4, sticky="ew")
            self.custom_min_entries.append(min_entry)
            
            ctk.CTkLabel(custom_frame, text="Max Torque (cNm):", font=ctk.CTkFont(size=10, weight="bold")).grid(row=2, column=0, padx=14, pady=4, sticky="w")
            max_entry = ctk.CTkEntry(custom_frame, placeholder_text="e.g. 50.0")
            max_entry.insert(0, str(self.settings_cache.get(f"custom_torque_max{suffix}", 50.0)))
            max_entry.grid(row=2, column=1, padx=14, pady=4, sticky="ew")
            self.custom_max_entries.append(max_entry)
            
            ctk.CTkLabel(custom_frame, text="Serial Regex Pattern:", font=ctk.CTkFont(size=10, weight="bold")).grid(row=3, column=0, padx=14, pady=4, sticky="w")
            pattern_entry = ctk.CTkEntry(custom_frame, placeholder_text=r"e.g. ([+-]?\d+\.\d+)\s*Nm")
            pattern_entry.insert(0, self.settings_cache.get(f"custom_serial_pattern{suffix}", r"([+-]?\d+\.\d+)\s*Nm"))
            pattern_entry.grid(row=3, column=1, padx=14, pady=4, sticky="ew")
            self.custom_pattern_entries.append(pattern_entry)
            
            self.custom_frame_widgets.append(custom_frame)
            if current_model == "Custom…":
                custom_frame.pack(fill="x", padx=10, pady=5)
                
            conn_status_lbl = ctk.CTkLabel(scroll, text="", font=ctk.CTkFont(size=12))
            conn_status_lbl.pack(pady=(10, 2))
            self.conn_status_lbls.append(conn_status_lbl)
            
            ctk.CTkButton(scroll, text="Check Sensor Status", fg_color="gray30", hover_color="gray40",
                          command=lambda i=idx: self.test_connection_by_idx(i)).pack(pady=4, fill="x", padx=15)
                          
            if self.is_admin:
                save_btn = ctk.CTkButton(scroll, text=f"Apply & Save Tester {letter}", fg_color="#1a7a3a", hover_color="#145e2c",
                              command=lambda i=idx: self.save_settings_by_idx(i))
                save_btn.pack(pady=(4, 4), fill="x", padx=15)
                
                # Only show Delete button if count > 2 (Tester A and B are core) and it's the last tester
                if tester_count > 2 and idx == tester_count - 1:
                    delete_btn = ctk.CTkButton(scroll, text=f"Delete Tester {letter}", fg_color="red4", hover_color="red3",
                                  command=lambda i=idx: self.delete_tester_slot(i))
                    delete_btn.pack(pady=(2, 14), fill="x", padx=15)
                              
            preview = ctk.CTkFrame(scroll, fg_color="gray12", corner_radius=6)
            preview.pack(fill="x", padx=10, pady=5)
            preview.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(preview, text=f"TESTER {letter} LIVE PREVIEW", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, columnspan=2, padx=14, pady=(10, 4), sticky="w")
            ctk.CTkLabel(preview, text="Status:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=1, column=0, padx=14, pady=4, sticky="w")
            
            live_status_val = ctk.CTkLabel(preview, text="OFFLINE", font=ctk.CTkFont(size=11, weight="bold"), text_color="red")
            live_status_val.grid(row=1, column=1, padx=14, pady=4, sticky="w")
            self.live_status_vals.append(live_status_val)
            
            ctk.CTkLabel(preview, text="Live Torque:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=2, column=0, padx=14, pady=4, sticky="w")
            live_torque_val = ctk.CTkLabel(preview, text="– – – cNm", font=ctk.CTkFont(size=15, weight="bold"), text_color="gray50")
            live_torque_val.grid(row=2, column=1, padx=14, pady=4, sticky="w")
            self.live_torque_vals.append(live_torque_val)
            
            ctk.CTkLabel(preview, text="Peak Torque:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=3, column=0, padx=14, pady=4, sticky="w")
            live_peak_val = ctk.CTkLabel(preview, text="– – – cNm", font=ctk.CTkFont(size=15, weight="bold"), text_color="gray50")
            live_peak_val.grid(row=3, column=1, padx=14, pady=4, sticky="w")
            self.live_peak_vals.append(live_peak_val)
            
            ctk.CTkButton(preview, text="Reset Peak", height=26, fg_color="gray30", hover_color="gray40",
                          command=lambda i=idx: self.reset_sensor_peak_by_idx(i)).grid(row=4, column=0, columnspan=2, padx=14, pady=(4, 6), sticky="ew")
            
            ctk.CTkLabel(preview, text="RAW SERIAL FRAME:", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray60").grid(row=5, column=0, columnspan=2, padx=14, pady=(6, 0), sticky="w")
            
            raw_textbox = ctk.CTkTextbox(preview, height=60, font=ctk.CTkFont(family="Courier", size=9), fg_color="#111111", text_color="#00ff99", state="disabled", wrap="char")
            raw_textbox.grid(row=6, column=0, columnspan=2, padx=14, pady=(2, 12), sticky="ew")
            self.raw_textboxes.append(raw_textbox)

        if self.is_admin and tester_count < 8:
            self.tabview_left.add("+")

        self.toggle_simulator_fields()

        # ── RIGHT PANEL: Logs and Data Management (Tabbed) ─────────────────────
        right_panel_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        right_panel_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_panel_frame.grid_columnconfigure(0, weight=1)
        right_panel_frame.grid_rowconfigure(0, weight=1)

        self.tabview_right = ctk.CTkTabview(right_panel_frame, fg_color="transparent")
        self.tabview_right.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        tab_logs = self.tabview_right.add("System Logs")
        tab_data = self.tabview_right.add("Data Management")

        # ──────── System Logs Tab Setup ────────
        tab_logs.grid_columnconfigure(0, weight=1)
        tab_logs.grid_rowconfigure(1, weight=1)

        log_header = ctk.CTkFrame(tab_logs, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", pady=(5, 5))
        log_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_header, text="SYSTEM ACTIONS & PORT COMM LOG",
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            log_header, text="Refresh", width=80, height=26,
            command=self.refresh_logs
        ).grid(row=0, column=1, sticky="e")

        self.log_textbox = ctk.CTkTextbox(tab_logs, font=ctk.CTkFont(family="Courier", size=9))
        self.log_textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 5))

        self.refresh_logs()

        # ──────── Data Management Tab Setup ────────
        tab_data.grid_columnconfigure(0, weight=1)
        
        scroll_data = ctk.CTkScrollableFrame(tab_data, fg_color="transparent")
        scroll_data.grid(row=0, column=0, sticky="nsew")
        scroll_data.grid_columnconfigure(0, weight=1)
        tab_data.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            scroll_data, text="DATABASE BACKUP & CSV EXPORT",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        # Driver Export Button
        ctk.CTkButton(
            scroll_data, text="Export Torque Drivers Database (CSV)",
            fg_color="gray30", hover_color="gray40", height=32,
            command=self.export_drivers
        ).pack(fill="x", padx=10, pady=5)

        # Test Procedures Export Button
        ctk.CTkButton(
            scroll_data, text="Export Test Procedures Database (CSV)",
            fg_color="gray30", hover_color="gray40", height=32,
            command=self.export_test_defs
        ).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            scroll_data, text="DATABASE RESTORE & CSV IMPORT",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=10, pady=(20, 5))

        # Driver Import Button
        ctk.CTkButton(
            scroll_data, text="Import Torque Drivers Database (CSV)",
            fg_color="#3366cc", hover_color="#224499", height=32,
            command=self.import_drivers,
            state="normal" if self.is_admin else "disabled"
        ).pack(fill="x", padx=10, pady=5)

        # Test Procedures Import Button
        ctk.CTkButton(
            scroll_data, text="Import Test Procedures Database (CSV)",
            fg_color="#3366cc", hover_color="#224499", height=32,
            command=self.import_test_defs,
            state="normal" if self.is_admin else "disabled"
        ).pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            scroll_data, text="DANGER ZONE",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ff3333"
        ).pack(anchor="w", padx=10, pady=(20, 5))

        # Reset All History Button
        ctk.CTkButton(
            scroll_data, text="Reset & Clear All Test Records (CSV Export First)",
            fg_color="#a83232", hover_color="#7a1e1e", height=32,
            command=self.reset_all_history,
            state="normal" if self.is_admin else "disabled"
        ).pack(fill="x", padx=10, pady=5)

        self.import_status_lbl = ctk.CTkLabel(
            scroll_data, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="green", wraplength=350
        )
        self.import_status_lbl.pack(padx=10, pady=15)

        # ──────── Database Location Tab Setup ────────
        tab_db = self.tabview_right.add("Database Location")
        tab_db.grid_columnconfigure(0, weight=1)
        
        scroll_db = ctk.CTkScrollableFrame(tab_db, fg_color="transparent")
        scroll_db.grid(row=0, column=0, sticky="nsew")
        scroll_db.grid_columnconfigure(0, weight=1)
        tab_db.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            scroll_db, text="DATABASE LOCATION CONFIGURATION",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        # DB Type Choice
        ctk.CTkLabel(scroll_db, text="Database Connection Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w", padx=10, pady=(5, 1))
        self.db_type_combo = ctk.CTkComboBox(
            scroll_db, 
            values=["SQLite (Local File)", "SQL Server (Online)"],
            state=self.state_ctrl,
            command=self.toggle_db_fields
        )
        current_db_type = self.app.db.db_config.get("db_type", "sqlite")
        self.db_type_combo.set("SQL Server (Online)" if current_db_type == "sql_server" else "SQLite (Local File)")
        self.db_type_combo.pack(fill="x", padx=10, pady=(0, 10))

        # SQLite Path Entry
        self.sqlite_lbl = ctk.CTkLabel(scroll_db, text="SQLite Local File Path:", font=ctk.CTkFont(size=11, weight="bold"))
        self.sqlite_lbl.pack(anchor="w", padx=10, pady=(5, 1))
        self.sqlite_entry = ctk.CTkEntry(scroll_db, placeholder_text="e.g. torque_tester.db")
        self.sqlite_entry.insert(0, self.app.db.db_config.get("sqlite_path", "torque_tester.db"))
        self.sqlite_entry.pack(fill="x", padx=10, pady=(0, 10))

        # SQL Server Conn Str Entry
        self.sqlserver_lbl = ctk.CTkLabel(scroll_db, text="SQL Server Connection String (ADO.NET / ODBC):", font=ctk.CTkFont(size=11, weight="bold"))
        self.sqlserver_lbl.pack(anchor="w", padx=10, pady=(5, 1))
        self.sqlserver_entry = ctk.CTkEntry(
            scroll_db, 
            placeholder_text="e.g. Data Source=pt4vo001\\sqlexpress,1433;Initial Catalog=Olympus_Test_v2;User ID=app_writer;Password=Ompp_1234;"
        )
        self.sqlserver_entry.insert(0, self.app.db.db_config.get("sql_server_conn_str", ""))
        self.sqlserver_entry.pack(fill="x", padx=10, pady=(0, 15))

        # Save Button
        self.save_db_config_btn = ctk.CTkButton(
            scroll_db, 
            text="Save DB Connection Settings & Restart", 
            fg_color="#1a7a3a", 
            hover_color="#145e2c",
            command=self.save_db_location_settings,
            state="normal" if self.is_admin else "disabled"
        )
        self.save_db_config_btn.pack(fill="x", padx=10, pady=5)

        self.toggle_db_fields()

        # Start polling
        self.is_active = True
        self.poll_sensor()

    def toggle_db_fields(self, choice=None):
        choice = choice or self.db_type_combo.get()
        if "SQL Server" in choice:
            self.sqlite_entry.configure(state="disabled")
            self.sqlserver_entry.configure(state="normal" if self.is_admin else "disabled")
        else:
            self.sqlite_entry.configure(state="normal" if self.is_admin else "disabled")
            self.sqlserver_entry.configure(state="disabled")

    def save_db_location_settings(self):
        from tkinter import messagebox
        db_choice = self.db_type_combo.get()
        db_type = "sql_server" if "SQL Server" in db_choice else "sqlite"
        sqlite_path = self.sqlite_entry.get().strip()
        sql_server_conn_str = self.sqlserver_entry.get().strip()

        if db_type == "sqlite" and not sqlite_path:
            messagebox.showerror("Validation Error", "SQLite file path cannot be empty.")
            return
        if db_type == "sql_server" and not sql_server_conn_str:
            messagebox.showerror("Validation Error", "SQL Server connection string cannot be empty.")
            return

        self.app.db.db_config["db_type"] = db_type
        self.app.db.db_config["sqlite_path"] = sqlite_path
        self.app.db.db_config["sql_server_conn_str"] = sql_server_conn_str
        self.app.db.save_db_config()

        messagebox.showinfo(
            "Settings Saved",
            "Database connection settings have been saved successfully.\n\n"
            "The application will now close. Please restart it to apply the new database configuration."
        )
        self.app.destroy()
