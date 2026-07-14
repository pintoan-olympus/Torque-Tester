import customtkinter as ctk
from utils.logger import get_logger, log_action
from views.components import ScrollableTable
from database.models import TestDefinition

logger = get_logger()

class TestSetupView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Selected test definition ID for editing
        self.selected_test_id = None
        self.selected_test_ids = set()
        
        # Grid layout (2 columns: left form, right registry table)
        self.grid_columnconfigure(0, weight=2, uniform="cols")
        self.grid_columnconfigure(1, weight=3, uniform="cols")
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: Test Procedure Form ---
        self.form_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray12")
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        self.form_title = ctk.CTkLabel(
            self.form_frame, 
            text="CREATE TEST PROCEDURE", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.form_title.pack(pady=(15, 10), padx=20, anchor="w")
        
        # Fields container (Scrollable to prevent overflow)
        scroll_fields = ctk.CTkScrollableFrame(self.form_frame, fg_color="transparent")
        scroll_fields.pack(fill="both", expand=True, padx=10, pady=5)
        scroll_fields.grid_columnconfigure(0, weight=1)
        
        # Test Name
        ctk.CTkLabel(scroll_fields, text="Procedure Name:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.name_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. Atlas Click Test 30cNm", height=38)
        self.name_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Test Type
        ctk.CTkLabel(scroll_fields, text="Evaluation Mode (Test Type):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.type_combo = ctk.CTkComboBox(
            scroll_fields, 
            values=["peak", "click", "preset", "breakaway", "residual"],
            height=38
        )
        self.type_combo.pack(fill="x", padx=10, pady=(0, 5))
        
        # Target Value
        ctk.CTkLabel(scroll_fields, text="Target Torque (cNm):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.target_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. 30.0", height=38)
        self.target_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        # Tolerances (+ / - cNm)
        tols_frame = ctk.CTkFrame(scroll_fields, fg_color="transparent")
        tols_frame.pack(fill="x", padx=10, pady=5)
        tols_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(tols_frame, text="Tolerance Plus (+ cNm):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w", padx=2)
        self.tol_plus_entry = ctk.CTkEntry(tols_frame, placeholder_text="e.g. 3.0", height=38)
        self.tol_plus_entry.grid(row=1, column=0, sticky="ew", padx=2)
        
        ctk.CTkLabel(tols_frame, text="Tolerance Minus (- cNm):", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w", padx=2)
        self.tol_minus_entry = ctk.CTkEntry(tols_frame, placeholder_text="e.g. 3.0", height=38)
        self.tol_minus_entry.grid(row=1, column=1, sticky="ew", padx=2)
        
        # Number of samples
        ctk.CTkLabel(scroll_fields, text="Quantity of measurements (Max Samples):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.samples_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. 5", height=38)
        self.samples_entry.pack(fill="x", padx=10, pady=(0, 5))

        # Min number of samples
        ctk.CTkLabel(scroll_fields, text="Minimum measurements (Min Samples):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.min_samples_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. 3", height=38)
        self.min_samples_entry.pack(fill="x", padx=10, pady=(0, 5))

        # Min OK samples to Pass
        ctk.CTkLabel(scroll_fields, text="Minimum OK to Pass (Min OK):", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        self.min_ok_entry = ctk.CTkEntry(scroll_fields, placeholder_text="e.g. 4", height=38)
        self.min_ok_entry.pack(fill="x", padx=10, pady=(0, 5))

        # Default Tester
        ctk.CTkLabel(scroll_fields, text="Default Tester:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=10, anchor="w")
        tester_count = self.app.hw_config.get_setting("tester_count", 2)
        tester_options = [f"Tester {chr(65 + i)}" for i in range(tester_count)]
        self.tester_combo = ctk.CTkComboBox(scroll_fields, values=tester_options, height=38)
        self.tester_combo.pack(fill="x", padx=10, pady=(0, 5))
        
        # Active Checkbox
        self.active_var = ctk.BooleanVar(value=True)
        self.active_cb = ctk.CTkCheckBox(scroll_fields, text="Procedure Active", variable=self.active_var)
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
            text="Save Template", 
            fg_color="green", 
            hover_color="darkgreen",
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.save_template
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
        
        # --- RIGHT PANEL: Test Definition Registry ---
        self.registry_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray12")
        self.registry_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.registry_frame.grid_columnconfigure(0, weight=1)
        self.registry_frame.grid_rowconfigure(2, weight=0)
        
        # Registry Title
        reg_title = ctk.CTkLabel(self.registry_frame, text="PROCEDURE TEMPLATES", font=ctk.CTkFont(size=14, weight="bold"))
        reg_title.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="w")

        # Search Bar Frame
        search_frame = ctk.CTkFrame(self.registry_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=0)
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search templates by Name, Type, or Tester...",
            height=38
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_templates())

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
        
        # Table
        self.table = ScrollableTable(
            self.registry_frame,
            headers=["Name", "Type", "Tester", "Target (cNm)", "Tolerances", "Qty", "Status"],
            column_weights=[3, 2, 1, 2, 2, 1, 2],
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
            command=self.edit_selected_template
        )
        self.edit_action_btn.pack(side="left", padx=10, pady=0)
        
        self.clone_action_btn = ctk.CTkButton(
            self.action_bar, text="Clone Selected", fg_color="gray30", hover_color="gray40",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.clone_selected_template
        )
        self.clone_action_btn.pack(side="left", padx=10, pady=0)
        
        self.delete_action_btn = ctk.CTkButton(
            self.action_bar, text="Delete Selected", fg_color="#a83232", hover_color="#7a1e1e",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.delete_selected_templates
        )
        self.delete_action_btn.pack(side="left", padx=10, pady=0)
        
        self.table_items = []
        self.load_templates()

    def filter_templates(self):
        self.load_templates()

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.load_templates()

    def load_templates(self):
        self.table.clear()
        test_defs = self.app.db.get_all_test_definitions()

        # Apply search filter
        query = self.search_entry.get().lower().strip() if hasattr(self, 'search_entry') else ""
        if query:
            test_defs = [
                td for td in test_defs
                if query in (td.name or "").lower() or
                   query in (td.test_type or "").lower() or
                   query in f"tester {getattr(td, 'default_tester_id', 'a')}".lower()
            ]
        
        self.table_items = test_defs
        
        for td in test_defs:
            status_disp = "Active" if td.active else "Inactive"
            row_color = "green" if td.active else "gray60"
            tol_disp = f"+{td.tolerance_plus}/-{td.tolerance_minus}"
            qty_disp = f"{td.min_samples}-{td.num_samples} (OK: {td.min_ok_samples})"
            tester_disp = f"Tester {getattr(td, 'default_tester_id', 'A')}"
            
            self.table.add_row(
                [
                    td.name,
                    td.test_type,
                    tester_disp,
                    f"{td.target_value:.2f}",
                    tol_disp,
                    qty_disp,
                    status_disp
                ],
                text_color=row_color
            )
            
        # Re-apply highlights after loading rows
        selected_indices = [
            idx for idx, td in enumerate(self.table_items)
            if td.id in self.selected_test_ids
        ]
        self.table.highlight_rows(selected_indices)

    def clone_template_selected(self, test_def: TestDefinition):
        self.edit_template_selected(test_def)
        # Clear name field to request a new name
        self.name_entry.delete(0, "end")
        self.selected_test_id = None
        self.form_title.configure(text="CLONE TEMPLATE - Enter New Name")

    def edit_template_selected(self, test_def: TestDefinition):
        self.selected_test_id = test_def.id
        self.form_title.configure(text=f"EDIT TEMPLATE ID #{test_def.id}")
        
        # Load fields
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, test_def.name)
        
        self.type_combo.set(test_def.test_type)
        
        self.target_entry.delete(0, "end")
        self.target_entry.insert(0, str(test_def.target_value))
        
        self.tol_plus_entry.delete(0, "end")
        self.tol_plus_entry.insert(0, str(test_def.tolerance_plus))
        
        self.tol_minus_entry.delete(0, "end")
        self.tol_minus_entry.insert(0, str(test_def.tolerance_minus))
        
        self.samples_entry.delete(0, "end")
        self.samples_entry.insert(0, str(test_def.num_samples))
        
        self.min_samples_entry.delete(0, "end")
        self.min_samples_entry.insert(0, str(test_def.min_samples))

        self.min_ok_entry.delete(0, "end")
        self.min_ok_entry.insert(0, str(test_def.min_ok_samples if test_def.min_ok_samples is not None else test_def.num_samples))
        
        self.tester_combo.set(f"Tester {getattr(test_def, 'default_tester_id', 'A')}")

        self.active_var.set(test_def.active)
        self.status_lbl.configure(text="")

    def clear_form(self, clear_selection=True):
        self.selected_test_id = None
        self.form_title.configure(text="CREATE TEST PROCEDURE")
        self.name_entry.delete(0, "end")
        self.type_combo.set("peak")
        self.target_entry.delete(0, "end")
        self.tol_plus_entry.delete(0, "end")
        self.tol_minus_entry.delete(0, "end")
        self.samples_entry.delete(0, "end")
        self.min_samples_entry.delete(0, "end")
        self.min_ok_entry.delete(0, "end")
        self.tester_combo.set("Tester A")
        self.active_var.set(True)
        self.status_lbl.configure(text="")
        
        if clear_selection:
            self.selected_test_ids.clear()
            self.table.highlight_rows([])
            self.update_action_bar_visibility()

    def on_row_clicked(self, row_idx: int, ctrl_pressed: bool):
        if row_idx < len(self.table_items):
            selected_template = self.table_items[row_idx]
            template_id = selected_template.id
            
            if ctrl_pressed:
                if template_id in self.selected_test_ids:
                    self.selected_test_ids.discard(template_id)
                else:
                    self.selected_test_ids.add(template_id)
            else:
                if len(self.selected_test_ids) == 1 and template_id in self.selected_test_ids:
                    self.selected_test_ids.clear()
                else:
                    self.selected_test_ids.clear()
                    self.selected_test_ids.add(template_id)
            
            selected_indices = [
                idx for idx, td in enumerate(self.table_items)
                if td.id in self.selected_test_ids
            ]
            self.table.highlight_rows(selected_indices)
            self.update_action_bar_visibility()
            
            if len(self.selected_test_ids) == 1:
                active_id = list(self.selected_test_ids)[0]
                active_td = next(td for td in self.table_items if td.id == active_id)
                self.edit_template_selected(active_td)
            else:
                self.clear_form(clear_selection=False)

    def update_action_bar_visibility(self):
        count = len(self.selected_test_ids)
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

    def edit_selected_template(self):
        if len(self.selected_test_ids) == 1:
            template_id = list(self.selected_test_ids)[0]
            template = next(td for td in self.table_items if td.id == template_id)
            self.edit_template_selected(template)

    def clone_selected_template(self):
        if len(self.selected_test_ids) == 1:
            template_id = list(self.selected_test_ids)[0]
            template = next(td for td in self.table_items if td.id == template_id)
            self.clone_template_selected(template)

    def delete_selected_templates(self):
        from tkinter import messagebox
        count = len(self.selected_test_ids)
        if count == 0:
            return
            
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the {count} selected procedure(s)?"
        )
        if not confirm:
            return
            
        success_count = 0
        deactivated_count = 0
        error_msgs = []
        
        template_ids_to_delete = list(self.selected_test_ids)
        
        for template_id in template_ids_to_delete:
            td_obj = next((td for td in self.table_items if td.id == template_id), None)
            if not td_obj:
                continue
                
            try:
                self.app.db.delete_test_definition(template_id)
                success_count += 1
                log_action(self.app.user_manager.current_user.username, "DELETE_TEST_TEMPLATE", f"Template: {td_obj.name}")
            except Exception as e:
                # Handle foreign key constraint failure
                if "FOREIGN KEY" in str(e).upper() or "CONSTRAINT" in str(e).upper():
                    deactivate_confirm = messagebox.askyesno(
                        "Historical Logs Found",
                        f"Procedure '{td_obj.name}' is referenced in historical logs and cannot be permanently deleted.\n\n"
                        "Would you like to deactivate it instead? (This will hide it from active test creation but keep the logs)."
                    )
                    if deactivate_confirm:
                        td_obj.active = False
                        if self.app.db.update_test_definition(td_obj):
                            deactivated_count += 1
                            log_action(self.app.user_manager.current_user.username, "DEACTIVATE_TEST_TEMPLATE", f"Template: {td_obj.name}")
                        else:
                            error_msgs.append(f"Failed to deactivate '{td_obj.name}'")
                else:
                    error_msgs.append(f"Error deleting '{td_obj.name}': {e}")
                    
        self.clear_form(clear_selection=True)
        self.load_templates()
        
        # Display completion status
        status_msg = f"Deleted {success_count} template(s)."
        if deactivated_count > 0:
            status_msg += f" Deactivated {deactivated_count} template(s)."
        if error_msgs:
            status_msg += f" Errors: {', '.join(error_msgs)}"
            self.status_lbl.configure(text=status_msg, text_color="red")
        else:
            self.status_lbl.configure(text=status_msg, text_color="green")

    def save_template(self):
        # Validate inputs
        name = self.name_entry.get().strip()
        test_type = self.type_combo.get()
        instructions = ""
        active = self.active_var.get()
        
        if not name:
            self.status_lbl.configure(text="Template name is required.")
            return
            
        try:
            target = float(self.target_entry.get().strip() or 0)
            tol_plus = float(self.tol_plus_entry.get().strip() or 0)
            tol_minus = float(self.tol_minus_entry.get().strip() or 0)
            samples = int(self.samples_entry.get().strip() or 5)
            min_samples = int(self.min_samples_entry.get().strip() or 3)
            min_ok = int(self.min_ok_entry.get().strip() or samples)
        except ValueError:
            self.status_lbl.configure(text="Torque values and samples must be numeric/integers.")
            return
            
        if target <= 0 or tol_plus < 0 or tol_minus < 0 or samples <= 0 or min_samples <= 0 or min_ok <= 0:
            self.status_lbl.configure(text="Target, tolerances and samples must be positive numbers.")
            return

        if min_samples > samples:
            self.status_lbl.configure(text="Min samples cannot exceed Max samples.")
            return
            
        if min_ok > samples:
            self.status_lbl.configure(text="Min OK to Pass cannot exceed Max Samples.")
            return

        tester_val = self.tester_combo.get().split()[-1]

        # Prepare object
        td_obj = TestDefinition(
            name=name,
            test_type=test_type,
            target_value=target,
            tolerance_plus=tol_plus,
            tolerance_minus=tol_minus,
            num_samples=samples,
            min_samples=min_samples,
            min_ok_samples=min_ok,
            default_tester_id=tester_val,
            instructions=instructions,
            active=active
        )
        
        if self.selected_test_id:
            # Update mode
            td_obj.id = self.selected_test_id
            success = self.app.db.update_test_definition(td_obj)
            action_log = "UPDATE_TEST_TEMPLATE"
        else:
            # Create mode
            success = self.app.db.create_test_definition(td_obj)
            action_log = "CREATE_TEST_TEMPLATE"
            
        if success:
            log_action(self.app.user_manager.current_user.username, action_log, f"Template: {name}")
            self.clear_form()
            self.load_templates()
        else:
            self.status_lbl.configure(text="Operation failed. Database error.")
