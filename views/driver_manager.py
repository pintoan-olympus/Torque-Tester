import customtkinter as ctk
from datetime import datetime
from utils.logger import get_logger, log_action
from utils.helpers import format_date
from views.components import ScrollableTable
from database.models import TorqueDriver
import i18n

logger = get_logger()

class DriverManagerView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Selected driver for editing (None means adding new)
        self.selected_driver_id = None
        
        # Multi-select tracking for bulk operations
        self.selected_driver_ids = set()
        
        # Grid layout (2 columns: left for form, right for registry table)
        self.grid_columnconfigure(0, weight=2, uniform="cols")
        self.grid_columnconfigure(1, weight=3, uniform="cols")
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: Driver Form ---
        self.form_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray12")
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        self.form_title = ctk.CTkLabel(
            self.form_frame, 
            text="REGISTER NEW DRIVER", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.form_title.pack(pady=(15, 10), padx=20, anchor="w")
        
        # Fields container (Scrollable to prevent overflow)
        scroll_fields = ctk.CTkScrollableFrame(self.form_frame, fg_color="transparent")
        scroll_fields.pack(fill="both", expand=True, padx=10, pady=5)
        scroll_fields.grid_columnconfigure(0, weight=1)
        
        # Driver ID
        ctk.CTkLabel(scroll_fields, text="Driver ID (Unique Tag):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.driver_id_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. DRV-001", height=38)
        self.driver_id_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Type
        ctk.CTkLabel(scroll_fields, text="Driver Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.type_combo = ctk.CTkComboBox(scroll_fields, values=["Electric", "Pneumatic", "Manual Click", "Screwdriver", "Hydraulic"], height=38)
        self.type_combo.pack(fill="x", padx=10, pady=(0, 5))
        
        # Brand & Model
        brand_model_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        brand_model_frame.pack(fill="x", padx=10, pady=5)
        brand_model_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(brand_model_frame, text="Brand:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.brand_entry = ctk.CTkEntry(brand_model_frame, placeholder_text="e.g. Atlas Copco", height=38)
        self.brand_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(brand_model_frame, text="Model:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.model_entry = ctk.CTkEntry(brand_model_frame, placeholder_text="e.g. MicroTorque", height=38)
        self.model_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Limits (Min/Max Torque cNm)
        limits_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        limits_frame.pack(fill="x", padx=10, pady=5)
        limits_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(limits_frame, text="Min Torque (cNm):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.min_entry = ctk.CTkEntry(limits_frame, placeholder_text="0.0", height=38)
        self.min_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(limits_frame, text="Max Torque (cNm):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.max_entry = ctk.CTkEntry(limits_frame, placeholder_text="50.0", height=38)
        self.max_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Workbench
        ctk.CTkLabel(scroll_fields, text="Assigned Workbench:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.workbench_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. Assembly Bench 4", height=38)
        self.workbench_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Calibration Dates (Last, Next)
        cal_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        cal_frame.pack(fill="x", padx=10, pady=5)
        cal_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(cal_frame, text="Last Calibration (YYYY-MM-DD):", font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.last_cal_entry = ctk.CTkEntry(cal_frame, placeholder_text="YYYY-MM-DD", height=38)
        self.last_cal_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(cal_frame, text="Calibration Due (YYYY-MM-DD):", font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.due_cal_entry = ctk.CTkEntry(cal_frame, placeholder_text="YYYY-MM-DD", height=38)
        self.due_cal_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Notes
        ctk.CTkLabel(scroll_fields, text="Notes:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.notes_entry = ctk.CTkEntry(scroll_fields, placeholder_text="Maintenance info...", height=38)
        self.notes_entry.pack(fill="x", padx=10, pady=(0, 5))

        # Default Test Template
        ctk.CTkLabel(scroll_fields, text="Default Test Template:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.default_test_combo = ctk.CTkComboBox(
            scroll_fields, 
            values=["None"],
            width=350,
            height=38
        )
        self.default_test_combo.pack(fill="x", padx=10, pady=(0, 5))
        # Handedness
        ctk.CTkLabel(scroll_fields, text="Handedness (Direction):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.handedness_combo = ctk.CTkComboBox(scroll_fields, values=["Right (CW, +)", "Left (CCW, -)"], height=38)
        self.handedness_combo.pack(fill="x", padx=10, pady=(0, 5))
        
        # Active Checkbox
        self.active_var = ctk.BooleanVar(value=True)
        self.active_cb = ctk.CTkCheckBox(scroll_fields, text="Active & Available", variable=self.active_var)
        self.active_cb.pack(pady=10, padx=10, anchor="w")
        
        # Form Status
        self.status_lbl = ctk.CTkLabel(self.form_frame, text="", text_color="red", font=ctk.CTkFont(size=12))
        self.status_lbl.pack(pady=5)
        
        # Form Buttons
        self.form_btn_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.form_btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        self.form_btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.save_btn = ctk.CTkButton(
            self.form_btn_frame, 
            text="Save Driver", 
            fg_color="green", 
            hover_color="darkgreen",
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.save_driver
        )
        self.save_btn.grid(row=0, column=0, padx=2, sticky="ew")
        
        self.clear_btn = ctk.CTkButton(
            self.form_btn_frame, 
            text="Clear Form", 
            fg_color="gray30", 
            hover_color="gray40", 
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.clear_form
        )
        self.clear_btn.grid(row=0, column=1, padx=2, sticky="ew")
        
        # --- RIGHT PANEL: Drivers Registry ---
        self.registry_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray12")
        self.registry_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.registry_frame.grid_columnconfigure(0, weight=1)
        self.registry_frame.grid_rowconfigure(2, weight=0)
        
        # Registry Title
        reg_title = ctk.CTkLabel(self.registry_frame, text="DRIVER REGISTRY", font=ctk.CTkFont(size=14, weight="bold"))
        reg_title.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="w")

        # Search Bar Frame
        search_frame = ctk.CTkFrame(self.registry_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=0)
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by Driver ID, Brand, Model, Type, or Workbench...",
            height=38
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_drivers())

        clear_search_btn = ctk.CTkButton(
            search_frame,
            text="Clear",
            width=60,
            height=38,
            fg_color="gray30",
            hover_color="gray40",
            command=self.clear_search
        )
        clear_search_btn.grid(row=0, column=1, sticky="e")
        
        clear_search_btn.grid(row=0, column=1, sticky="e")
        
        # Table
        self.table = ScrollableTable(
            self.registry_frame,
            headers=["ID", "Type", "Hand", "Workbench", "Range (cNm)", "Cal Due", "Status"],
            column_weights=[2, 2, 1, 2, 2, 2, 2],
            row_click_callback=self.on_row_clicked,
            fg_color="gray12"
        )
        self.table.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.registry_frame.grid_rowconfigure(3, weight=1)

        # Action Bar (Edit, Clone, Delete) - hidden initially
        self.action_bar = ctk.CTkFrame(self.registry_frame, fg_color="gray18", corner_radius=6)
        
        self.edit_action_btn = ctk.CTkButton(
            self.action_bar, text="Edit Selected", fg_color="#3a86ff", hover_color="#2b6bcf",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.edit_selected_driver
        )
        self.edit_action_btn.pack(side="left", padx=10, pady=0)
        
        self.clone_action_btn = ctk.CTkButton(
            self.action_bar, text="Clone Selected", fg_color="gray30", hover_color="gray40",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.clone_selected_driver
        )
        self.clone_action_btn.pack(side="left", padx=10, pady=0)
        
        self.delete_action_btn = ctk.CTkButton(
            self.action_bar, text="Delete Selected", fg_color="#a83232", hover_color="#7a1e1e",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.delete_selected_drivers
        )
        self.delete_action_btn.pack(side="left", padx=10, pady=0)

        # Bulk Edit Action Bar (hidden initially)
        self.bulk_bar = ctk.CTkFrame(self.registry_frame, fg_color="gray18", corner_radius=6)
        
        self.bulk_lbl = ctk.CTkLabel(self.bulk_bar, text="Default test edit (0 selected):", font=ctk.CTkFont(size=12, weight="bold"))
        self.bulk_lbl.pack(side="left", padx=10, pady=10)

        self.bulk_test_var = ctk.StringVar()
        self.bulk_test_combo = ctk.CTkComboBox(self.bulk_bar, values=[], variable=self.bulk_test_var, width=180)
        self.bulk_test_combo.pack(side="left", padx=5, pady=10)

        self.bulk_apply_btn = ctk.CTkButton(
            self.bulk_bar, 
            text="Apply to Selected", 
            width=120, 
            fg_color="green", 
            hover_color="darkgreen",
            command=self.apply_bulk_edit
        )
        self.bulk_apply_btn.pack(side="left", padx=5, pady=10)

        self.bulk_clear_btn = ctk.CTkButton(
            self.bulk_bar, 
            text="Clear Selection", 
            width=100, 
            fg_color="gray30", 
            hover_color="gray40",
            command=self.clear_driver_selection
        )
        self.bulk_clear_btn.pack(side="right", padx=10, pady=10)
        
        self.table_items = []
        self.load_drivers()

    def on_row_clicked(self, row_idx: int, ctrl_pressed: bool):
        if row_idx < len(self.table_items):
            selected_driver = self.table_items[row_idx]
            driver_id = selected_driver.id
            
            if ctrl_pressed:
                if driver_id in self.selected_driver_ids:
                    self.selected_driver_ids.discard(driver_id)
                else:
                    self.selected_driver_ids.add(driver_id)
            else:
                if len(self.selected_driver_ids) == 1 and driver_id in self.selected_driver_ids:
                    self.selected_driver_ids.clear()
                else:
                    self.selected_driver_ids.clear()
                    self.selected_driver_ids.add(driver_id)
            
            # Map selected IDs to row indices in self.table_items to highlight
            selected_indices = [
                idx for idx, d in enumerate(self.table_items)
                if d.id in self.selected_driver_ids
            ]
            self.table.highlight_rows(selected_indices)
            
            self.update_action_bar_visibility()
            self.update_bulk_bar_visibility()
            
            # If exactly 1 driver is selected, load it into the form for editing
            if len(self.selected_driver_ids) == 1:
                active_id = list(self.selected_driver_ids)[0]
                active_drv = next(d for d in self.table_items if d.id == active_id)
                self.edit_driver_selected(active_drv)
            else:
                self.clear_form(clear_selection=False)

    def update_action_bar_visibility(self):
        count = len(self.selected_driver_ids)
        if count == 1:
            self.action_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=0)
            self.edit_action_btn.pack(side="left", padx=10, pady=0)
            self.clone_action_btn.pack(side="left", padx=10, pady=0)
            self.delete_action_btn.pack(side="left", padx=10, pady=0)
            self.delete_action_btn.configure(text="Delete Selected")
        elif count > 1:
            self.action_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=0)
            self.edit_action_btn.pack_forget()
            self.clone_action_btn.pack_forget()
            self.delete_action_btn.pack(side="left", padx=10, pady=0)
            self.delete_action_btn.configure(text=f"Delete {count} Selected")
        else:
            self.action_bar.grid_forget()

    def edit_selected_driver(self):
        if len(self.selected_driver_ids) == 1:
            driver_id = list(self.selected_driver_ids)[0]
            driver = next(d for d in self.table_items if d.id == driver_id)
            self.edit_driver_selected(driver)

    def clone_selected_driver(self):
        if len(self.selected_driver_ids) == 1:
            driver_id = list(self.selected_driver_ids)[0]
            driver = next(d for d in self.table_items if d.id == driver_id)
            self.clone_driver_selected(driver)

    def delete_selected_drivers(self):
        from tkinter import messagebox
        count = len(self.selected_driver_ids)
        if count == 0:
            return
            
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the {count} selected driver(s)?"
        )
        if not confirm:
            return
            
        success_count = 0
        deactivated_count = 0
        error_msgs = []
        
        # Make a copy of selected IDs since we will clear selection
        driver_ids_to_delete = list(self.selected_driver_ids)
        
        for driver_id in driver_ids_to_delete:
            driver_obj = next((d for d in self.table_items if d.id == driver_id), None)
            if not driver_obj:
                continue
                
            try:
                self.app.db.delete_driver(driver_id)
                success_count += 1
                log_action(self.app.user_manager.current_user.username, "DELETE_DRIVER", f"Driver ID: {driver_obj.driver_id}")
            except Exception as e:
                # Handle foreign key constraint failure
                if "FOREIGN KEY" in str(e).upper() or "CONSTRAINT" in str(e).upper():
                    deactivate_confirm = messagebox.askyesno(
                        "Historical Logs Found",
                        f"Driver '{driver_obj.driver_id}' has historical test session logs and cannot be permanently deleted.\n\n"
                        "Would you like to deactivate it instead? (This will hide it from the dashboard but keep the logs)."
                    )
                    if deactivate_confirm:
                        driver_obj.active = False
                        if self.app.db.update_driver(driver_obj):
                            deactivated_count += 1
                            log_action(self.app.user_manager.current_user.username, "DEACTIVATE_DRIVER", f"Driver ID: {driver_obj.driver_id}")
                        else:
                            error_msgs.append(f"Failed to deactivate '{driver_obj.driver_id}'")
                else:
                    error_msgs.append(f"Error deleting '{driver_obj.driver_id}': {e}")
                    
        self.clear_form(clear_selection=True)
        self.load_drivers()
        
        # Display completion status
        status_msg = f"Deleted {success_count} driver(s)."
        if deactivated_count > 0:
            status_msg += f" Deactivated {deactivated_count} driver(s)."
        if error_msgs:
            status_msg += f" Errors: {', '.join(error_msgs)}"
            self.status_lbl.configure(text=status_msg, text_color="red")
        else:
            self.status_lbl.configure(text=status_msg, text_color="green")

    def update_bulk_bar_visibility(self):
        count = len(self.selected_driver_ids)
        if count > 0:
            self.bulk_lbl.configure(text=f"Default test edit ({count} selected):")
            self.bulk_bar.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 10))
        else:
            self.bulk_bar.grid_forget()

    def clear_driver_selection(self):
        self.selected_driver_ids.clear()
        self.load_drivers()
        self.update_action_bar_visibility()
        self.update_bulk_bar_visibility()

    def apply_bulk_edit(self):
        choice = self.bulk_test_var.get()
        test_def_id = None
        battery_id = None
        if choice.startswith("[Test] ") and choice in self.test_def_map:
            test_def_id = self.test_def_map[choice].id
        elif choice.startswith("[Battery] ") and choice in self.battery_map:
            battery_id = self.battery_map[choice].id
            
        driver_ids = list(self.selected_driver_ids)
        if driver_ids:
            updated = self.app.db.bulk_update_driver_default_test(driver_ids, test_def_id, battery_id)
            self.status_lbl.configure(text=f"Successfully updated default test/battery for {updated} drivers.", text_color="green")
            log_action(
                self.app.user_manager.current_user.username,
                "UPDATE_DRIVERS_BULK",
                f"Updated default test to {choice} for {updated} drivers."
            )
            self.clear_driver_selection()

    def filter_drivers(self):
        self.load_drivers()

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.load_drivers()

    def refresh_test_templates(self):
        test_defs = self.app.db.get_all_test_definitions()
        self.test_names = ["None"]
        self.test_def_map = {}
        self.test_def_id_map = {td.id: td for td in test_defs}
        for td in test_defs:
            if td.active:
                name = f"[Test] {td.name}"
                self.test_names.append(name)
                self.test_def_map[name] = td

        # Also load batteries
        batteries = self.app.db.get_all_batteries()
        self.battery_map = {}
        self.battery_id_map = {b.id: b for b in batteries}
        for b in batteries:
            if b.active:
                name = f"[Battery] {b.name}"
                self.test_names.append(name)
                self.battery_map[name] = b

        self.default_test_combo.configure(values=self.test_names)
        self.bulk_test_combo.configure(values=self.test_names)

    def load_drivers(self):
        self.refresh_test_templates()
        self.table.clear()
        drivers = self.app.db.get_all_drivers()
        
        # Apply filter
        search_widget = getattr(self, 'search_entry', None)
        query = search_widget.get().lower() if search_widget else ""
        if query:
            drivers = [
                d for d in drivers 
                if query in (d.driver_id or "").lower() or
                   query in (d.brand or "").lower() or
                   query in (d.model or "").lower() or
                   query in (d.driver_type or "").lower() or
                   query in (d.workbench or "").lower()
            ]
        
        self.table_items = drivers
        
        for d in drivers:
            # Check calibration due
            is_overdue = False
            cal_str = format_date(d.calibration_due)
            if d.calibration_due:
                try:
                    due = datetime.strptime(d.calibration_due, "%Y-%m-%d").date()
                    if due < datetime.now().date():
                        is_overdue = True
                except ValueError:
                    pass
            
            row_color = "red" if is_overdue else ("green" if d.active else "gray60")
            cal_disp = f"{cal_str} ⚠️" if is_overdue else cal_str
            active_disp = "Active" if d.active else "Inactive"
            hand_disp = "LH" if getattr(d, 'handedness', 'right') == 'left' else "RH"
            
            self.table.add_row(
                [
                    d.driver_id,
                    d.driver_type,
                    hand_disp,
                    d.workbench,
                    f"{d.torque_min}-{d.torque_max}",
                    cal_disp,
                    active_disp
                ],
                text_color=row_color
            )
            
        # Re-apply highlights after loading rows
        selected_indices = [
            idx for idx, d in enumerate(self.table_items)
            if d.id in self.selected_driver_ids
        ]
        self.table.highlight_rows(selected_indices)

    def clone_driver_selected(self, driver: TorqueDriver):
        self.edit_driver_selected(driver)
        self.driver_id_entry.configure(state="normal")
        self.driver_id_entry.delete(0, "end")
        self.selected_driver_id = None
        self.form_title.configure(text="CLONE DRIVER - Enter New Driver ID")

    def edit_driver_selected(self, driver: TorqueDriver):
        self.selected_driver_id = driver.id
        self.form_title.configure(text=f"EDIT DRIVER ID #{driver.driver_id}")
        self.driver_id_entry.configure(state="normal")
        
        # Load fields
        self.driver_id_entry.delete(0, "end")
        self.driver_id_entry.insert(0, driver.driver_id)
        # Lock driver_id editing for primary key preservation consistency
        self.driver_id_entry.configure(state="disabled")
        
        self.type_combo.set(driver.driver_type)
        
        self.brand_entry.delete(0, "end")
        self.brand_entry.insert(0, driver.brand or "")
        
        self.model_entry.delete(0, "end")
        self.model_entry.insert(0, driver.model or "")
        
        self.min_entry.delete(0, "end")
        self.min_entry.insert(0, str(driver.torque_min))
        
        self.max_entry.delete(0, "end")
        self.max_entry.insert(0, str(driver.torque_max))
        
        self.workbench_entry.delete(0, "end")
        self.workbench_entry.insert(0, driver.workbench or "")
        
        self.last_cal_entry.delete(0, "end")
        self.last_cal_entry.insert(0, driver.calibration_date or "")
        
        self.due_cal_entry.delete(0, "end")
        self.due_cal_entry.insert(0, driver.calibration_due or "")
        
        self.notes_entry.delete(0, "end")
        self.notes_entry.insert(0, driver.notes or "")

        # Select the default test template or battery name
        if driver.default_test_def_id and driver.default_test_def_id in self.test_def_id_map:
            default_test_name = f"[Test] {self.test_def_id_map[driver.default_test_def_id].name}"
            self.default_test_combo.set(default_test_name)
        elif getattr(driver, 'default_battery_id', None) and driver.default_battery_id in self.battery_id_map:
            default_test_name = f"[Battery] {self.battery_id_map[driver.default_battery_id].name}"
            self.default_test_combo.set(default_test_name)
        else:
            self.default_test_combo.set("None")
            
        hand_val = "Left (CCW, -)" if getattr(driver, 'handedness', 'right') == "left" else "Right (CW, +)"
        self.handedness_combo.set(hand_val)
        
        self.active_var.set(driver.active)
        self.status_lbl.configure(text="")

    def clear_form(self, clear_selection=True):
        self.selected_driver_id = None
        self.form_title.configure(text="REGISTER NEW DRIVER")
        self.driver_id_entry.configure(state="normal")
        self.driver_id_entry.delete(0, "end")
        self.type_combo.set("Electric")
        self.brand_entry.delete(0, "end")
        self.model_entry.delete(0, "end")
        self.min_entry.delete(0, "end")
        self.max_entry.delete(0, "end")
        self.workbench_entry.delete(0, "end")
        self.last_cal_entry.delete(0, "end")
        self.due_cal_entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self.default_test_combo.set("None")
        self.handedness_combo.set("Right (CW, +)")
        self.active_var.set(True)
        self.status_lbl.configure(text="")
        
        if clear_selection:
            self.selected_driver_ids.clear()
            self.table.highlight_rows([])
            self.update_action_bar_visibility()
            self.update_bulk_bar_visibility()

    def save_driver(self):
        # Validate inputs
        d_id = self.driver_id_entry.get().strip()
        d_type = self.type_combo.get()
        brand = self.brand_entry.get().strip()
        model = self.model_entry.get().strip()
        workbench = self.workbench_entry.get().strip()
        last_cal = self.last_cal_entry.get().strip() or None
        due_cal = self.due_cal_entry.get().strip() or None
        notes = self.notes_entry.get().strip()
        active = self.active_var.get()
        
        if not d_id or not workbench:
            self.status_lbl.configure(text="Driver ID and Workbench are required.")
            return
            
        try:
            torque_min = float(self.min_entry.get().strip() or 0)
            torque_max = float(self.max_entry.get().strip() or 0)
        except ValueError:
            self.status_lbl.configure(text="Torque limits must be numeric values.")
            return
            
        # Date regex check
        date_pattern = r"^\d{4}-\d{2}-\d{2}$"
        import re
        if last_cal and not re.match(date_pattern, last_cal):
            self.status_lbl.configure(text="Last Calibration must match YYYY-MM-DD.")
            return
        if due_cal and not re.match(date_pattern, due_cal):
            self.status_lbl.configure(text="Calibration Due must match YYYY-MM-DD.")
            return
            
        # Default test template ID resolving
        selected_test_name = self.default_test_combo.get()
        default_test_id = None
        default_battery_id = None
        if selected_test_name.startswith("[Test] ") and selected_test_name in self.test_def_map:
            default_test_id = self.test_def_map[selected_test_name].id
        elif selected_test_name.startswith("[Battery] ") and selected_test_name in self.battery_map:
            default_battery_id = self.battery_map[selected_test_name].id

        hand_val = "left" if "Left" in self.handedness_combo.get() else "right"

        # Prepare object
        driver_obj = TorqueDriver(
            driver_id=d_id,
            driver_type=d_type,
            brand=brand,
            model=model,
            torque_min=torque_min,
            torque_max=torque_max,
            workbench=workbench,
            calibration_date=last_cal,
            calibration_due=due_cal,
            notes=notes,
            active=active,
            default_test_def_id=default_test_id,
            default_battery_id=default_battery_id,
            handedness=hand_val
        )
        
        if self.selected_driver_id:
            # Update mode
            driver_obj.id = self.selected_driver_id
            success = self.app.db.update_driver(driver_obj)
            action_log = "UPDATE_DRIVER"
        else:
            # Create mode
            success = self.app.db.create_driver(driver_obj)
            action_log = "REGISTER_DRIVER"
            
        if success:
            log_action(self.app.user_manager.current_user.username, action_log, f"Driver ID: {d_id}")
            self.clear_form()
            self.load_drivers()
        else:
            self.status_lbl.configure(text="Operation failed. Driver ID may not be unique.")
pre_check_driver = None
