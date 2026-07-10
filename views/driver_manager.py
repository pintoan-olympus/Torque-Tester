import customtkinter as ctk
from datetime import datetime
from utils.logger import get_logger, log_action
from utils.helpers import format_date
from views.components import ScrollableTable
from database.models import TorqueDriver

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
        self.form_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
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
        self.driver_id_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. DRV-001")
        self.driver_id_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Type
        ctk.CTkLabel(scroll_fields, text="Driver Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.type_combo = ctk.CTkComboBox(scroll_fields, values=["Electric", "Pneumatic", "Manual Click", "Screwdriver", "Hydraulic"])
        self.type_combo.pack(fill="x", padx=10, pady=(0, 5))
        
        # Brand & Model
        brand_model_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        brand_model_frame.pack(fill="x", padx=10, pady=5)
        brand_model_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(brand_model_frame, text="Brand:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.brand_entry = ctk.CTkEntry(brand_model_frame, placeholder_text="e.g. Atlas Copco")
        self.brand_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(brand_model_frame, text="Model:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.model_entry = ctk.CTkEntry(brand_model_frame, placeholder_text="e.g. MicroTorque")
        self.model_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Limits (Min/Max Torque cNm)
        limits_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        limits_frame.pack(fill="x", padx=10, pady=5)
        limits_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(limits_frame, text="Min Torque (cNm):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.min_entry = ctk.CTkEntry(limits_frame, placeholder_text="0.0")
        self.min_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(limits_frame, text="Max Torque (cNm):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.max_entry = ctk.CTkEntry(limits_frame, placeholder_text="50.0")
        self.max_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Workbench
        ctk.CTkLabel(scroll_fields, text="Assigned Workbench:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.workbench_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. Assembly Bench 4")
        self.workbench_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Calibration Dates (Last, Next)
        cal_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        cal_frame.pack(fill="x", padx=10, pady=5)
        cal_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(cal_frame, text="Last Calibration (YYYY-MM-DD):", font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.last_cal_entry = ctk.CTkEntry(cal_frame, placeholder_text="YYYY-MM-DD")
        self.last_cal_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(cal_frame, text="Calibration Due (YYYY-MM-DD):", font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.due_cal_entry = ctk.CTkEntry(cal_frame, placeholder_text="YYYY-MM-DD")
        self.due_cal_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Notes
        ctk.CTkLabel(scroll_fields, text="Notes:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.notes_entry = ctk.CTkEntry(scroll_fields, placeholder_text="Maintenance info...")
        self.notes_entry.pack(fill="x", padx=10, pady=(0, 5))

        # Default Test Template
        ctk.CTkLabel(scroll_fields, text="Default Test Template:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.default_test_combo = ctk.CTkComboBox(
            scroll_fields, 
            values=["None"],
            width=350
        )
        self.default_test_combo.pack(fill="x", padx=10, pady=(0, 5))
        # Handedness
        ctk.CTkLabel(scroll_fields, text="Handedness (Direction):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.handedness_combo = ctk.CTkComboBox(scroll_fields, values=["Right (CW, +)", "Left (CCW, -)"])
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
            command=self.save_driver
        )
        self.save_btn.grid(row=0, column=0, padx=2, sticky="ew")
        
        self.clear_btn = ctk.CTkButton(
            self.form_btn_frame, 
            text="Clear Form", 
            fg_color="gray30", 
            hover_color="gray40", 
            command=self.clear_form
        )
        self.clear_btn.grid(row=0, column=1, padx=2, sticky="ew")
        
        # --- RIGHT PANEL: Drivers Registry ---
        self.registry_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.registry_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.registry_frame.grid_columnconfigure(0, weight=1)
        self.registry_frame.grid_rowconfigure(2, weight=1)
        
        # Registry Title
        reg_title = ctk.CTkLabel(self.registry_frame, text="DRIVER REGISTRY", font=ctk.CTkFont(size=14, weight="bold"))
        reg_title.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="w")

        # Search Bar Frame
        search_frame = ctk.CTkFrame(self.registry_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by Driver ID, Brand, Model, Type, or Workbench..."
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_drivers())

        clear_search_btn = ctk.CTkButton(
            search_frame,
            text="Clear",
            width=60,
            fg_color="gray30",
            hover_color="gray40",
            command=self.clear_search
        )
        clear_search_btn.grid(row=0, column=1, sticky="e")
        
        clear_search_btn.grid(row=0, column=1, sticky="e")
        
        # Table
        self.table = ScrollableTable(
            self.registry_frame,
            headers=["☐", "ID", "Type", "Hand", "Workbench", "Range (cNm)", "Cal Due", "Status", "Edit", "Clone"],
            column_weights=[1, 2, 2, 1, 2, 2, 2, 2, 1, 1],
            fg_color="gray12"
        )
        self.table.grid(row=2, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Replace first header label with a checkbox
        self.table.header_widgets[0].destroy()
        self.select_all_var = ctk.BooleanVar(value=False)
        self.select_all_cb = ctk.CTkCheckBox(
            self.table, 
            text="", 
            variable=self.select_all_var, 
            width=20,
            command=self.toggle_select_all
        )
        self.select_all_cb.grid(row=0, column=0, sticky="w", padx=10, pady=(0, 5))
        self.table.header_widgets[0] = self.select_all_cb

        # Bulk Edit Action Bar (hidden initially)
        self.bulk_bar = ctk.CTkFrame(self.registry_frame, fg_color="gray18", corner_radius=6)
        
        self.bulk_lbl = ctk.CTkLabel(self.bulk_bar, text="Bulk Edit (0 selected):", font=ctk.CTkFont(size=12, weight="bold"))
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
        
        self.load_drivers()

    def toggle_select_all(self):
        drivers = self.app.db.get_all_drivers()
        # Find currently filtered drivers
        search_query = self.search_entry.get().lower() if getattr(self, 'search_entry', None) else ""
        filtered_drivers = [
            d for d in drivers 
            if not search_query or
               search_query in (d.driver_id or "").lower() or
               search_query in (d.brand or "").lower() or
               search_query in (d.model or "").lower() or
               search_query in (d.driver_type or "").lower() or
               search_query in (d.workbench or "").lower()
        ]
        
        if self.select_all_var.get():
            for d in filtered_drivers:
                self.selected_driver_ids.add(d.id)
        else:
            for d in filtered_drivers:
                self.selected_driver_ids.discard(d.id)
                
        self.load_drivers()
        self.update_bulk_bar_visibility()

    def on_driver_chk_toggled(self, driver_id, is_checked):
        if is_checked:
            self.selected_driver_ids.add(driver_id)
        else:
            self.selected_driver_ids.discard(driver_id)
            self.select_all_var.set(False)
        self.update_bulk_bar_visibility()

    def update_bulk_bar_visibility(self):
        count = len(self.selected_driver_ids)
        if count > 0:
            self.bulk_lbl.configure(text=f"Bulk Edit ({count} selected):")
            self.bulk_bar.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 10))
        else:
            self.bulk_bar.grid_forget()

    def clear_driver_selection(self):
        self.selected_driver_ids.clear()
        self.select_all_var.set(False)
        self.load_drivers()
        self.update_bulk_bar_visibility()

    def apply_bulk_edit(self):
        choice = self.bulk_test_var.get()
        test_def_id = None
        if choice != "None" and choice in self.test_def_map:
            test_def_id = self.test_def_map[choice].id
            
        driver_ids = list(self.selected_driver_ids)
        if driver_ids:
            updated = self.app.db.bulk_update_driver_default_test(driver_ids, test_def_id)
            self.status_lbl.configure(text=f"Successfully updated default test for {updated} drivers.", text_color="green")
            log_action(
                self.app.user_manager.current_user.username,
                "UPDATE_DRIVERS_BULK",
                f"Updated default test ID to {test_def_id} for {updated} drivers."
            )
            self.clear_driver_selection()

    def filter_drivers(self):
        self.load_drivers()

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.load_drivers()

    def refresh_test_templates(self):
        test_defs = self.app.db.get_all_test_definitions()
        self.test_names = ["None"] + [td.name for td in test_defs if td.active]
        self.test_def_map = {td.name: td for td in test_defs if td.active}
        self.test_def_id_map = {td.id: td for td in test_defs}
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
            
            is_checked = d.id in self.selected_driver_ids
            def make_chk(parent, d_id=d.id, val_checked=is_checked):
                var = ctk.BooleanVar(value=val_checked)
                cb = ctk.CTkCheckBox(
                    parent, 
                    text="", 
                    variable=var, 
                    width=20,
                    command=lambda: self.on_driver_chk_toggled(d_id, var.get())
                )
                return cb

            cell_commands = {
                8: lambda driver_obj=d: self.edit_driver_selected(driver_obj),
                9: lambda driver_obj=d: self.clone_driver_selected(driver_obj)
            }
            
            self.table.add_row(
                [
                    make_chk,
                    d.driver_id,
                    d.driver_type,
                    hand_disp,
                    d.workbench,
                    f"{d.torque_min}-{d.torque_max}",
                    cal_disp,
                    active_disp,
                    "Edit",
                    "Clone"
                ],
                text_color=row_color,
                cell_commands=cell_commands
            )

    def clone_driver_selected(self, driver: TorqueDriver):
        self.edit_driver_selected(driver)
        self.driver_id_entry.configure(state="normal")
        self.driver_id_entry.delete(0, "end")
        self.selected_driver_id = None
        self.form_title.configure(text="CLONE DRIVER - Enter New Driver ID")

    def edit_driver_selected(self, driver: TorqueDriver):
        self.selected_driver_id = driver.id
        self.form_title.configure(text=f"EDIT DRIVER ID #{driver.id}")
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

        # Select the default test template name
        if driver.default_test_def_id and driver.default_test_def_id in self.test_def_id_map:
            default_test_name = self.test_def_id_map[driver.default_test_def_id].name
            self.default_test_combo.set(default_test_name)
        else:
            self.default_test_combo.set("None")
            
        hand_val = "Left (CCW, -)" if getattr(driver, 'handedness', 'right') == "left" else "Right (CW, +)"
        self.handedness_combo.set(hand_val)
        
        self.active_var.set(driver.active)
        self.status_lbl.configure(text="")

    def clear_form(self):
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
        if selected_test_name != "None" and selected_test_name in self.test_def_map:
            default_test_id = self.test_def_map[selected_test_name].id

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
