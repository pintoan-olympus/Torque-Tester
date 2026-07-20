import customtkinter as ctk
from datetime import datetime
from utils.logger import get_logger, log_action
from views.components import ScrollableTable
from database.models import TestBattery, BatteryItem, TestDefinition

logger = get_logger()

class BatterySetupView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.selected_battery_id = None
        self.selected_battery_ids = set()
        self.sequence = [] # List of TestDefinition objects in sequence

        # Configuration: 2 columns (weight 2:3)
        self.grid_columnconfigure(0, weight=2, uniform="cols")
        self.grid_columnconfigure(1, weight=3, uniform="cols")
        self.grid_rowconfigure(0, weight=1)

        # --- LEFT PANEL: Battery Form ---
        self.form_panel = ctk.CTkFrame(self, corner_radius=10, fg_color="gray12")
        self.form_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form_panel.grid_columnconfigure(0, weight=1)
        self.form_panel.grid_rowconfigure(5, weight=1) # Steps list takes space

        # Section Title
        lbl = ctk.CTkLabel(self.form_panel, text="BATTERY EDITOR", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(pady=(15, 10), padx=20, anchor="w")

        # Battery Name
        lbl_name = ctk.CTkLabel(self.form_panel, text="Battery Name (Required)", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_name.pack(pady=(5, 2), padx=20, anchor="w")
        self.name_entry = ctk.CTkEntry(self.form_panel, placeholder_text="e.g. Standard Battery Setup", height=38)
        self.name_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Description
        lbl_desc = ctk.CTkLabel(self.form_panel, text="Description", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_desc.pack(pady=(5, 2), padx=20, anchor="w")
        self.desc_entry = ctk.CTkEntry(self.form_panel, placeholder_text="e.g. Comprehensive calibration tests", height=38)
        self.desc_entry.pack(fill="x", padx=20, pady=(0, 10))

        # Active status checkbox
        self.active_var = ctk.BooleanVar(value=True)
        self.active_cb = ctk.CTkCheckBox(self.form_panel, text="Active", variable=self.active_var, fg_color="green")
        self.active_cb.pack(padx=20, pady=(5, 15), anchor="w")

        # Add steps label
        lbl_steps = ctk.CTkLabel(self.form_panel, text="Battery Test Steps Sequence", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_steps.pack(pady=(5, 2), padx=20, anchor="w")

        # List of added steps container
        self.steps_outer = ctk.CTkFrame(self.form_panel, fg_color="gray12", height=150)
        self.steps_outer.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        self.steps_outer.pack_propagate(False)

        self.steps_scroll = ctk.CTkScrollableFrame(self.steps_outer, fg_color="transparent")
        self.steps_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Dropdown selection of test definitions to add
        self.add_step_frame = ctk.CTkFrame(self.form_panel, fg_color="transparent")
        self.add_step_frame.pack(fill="x", padx=20, pady=(0, 15))

        test_defs = self.app.db.get_all_test_definitions()
        self.test_names = [td.name for td in test_defs if td.active]
        self.test_def_map = {td.name: td for td in test_defs if td.active}

        self.add_combo_var = ctk.StringVar()
        self.add_combo = ctk.CTkComboBox(
            self.add_step_frame,
            values=self.test_names,
            variable=self.add_combo_var,
            height=38,
            state="disabled" if not self.test_names else "normal"
        )
        self.add_combo.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.add_step_btn = ctk.CTkButton(
            self.add_step_frame,
            text="+ Add",
            width=60,
            height=38,
            command=self.add_step_to_sequence
        )
        self.add_step_btn.pack(side="right")

        # Status output line
        self.status_lbl = ctk.CTkLabel(self.form_panel, text="", font=ctk.CTkFont(size=11))
        self.status_lbl.pack(pady=(0, 5), padx=20)

        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self.form_panel, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.save_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Save Battery", 
            fg_color="green", 
            hover_color="darkgreen", 
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.save_battery
        )
        self.save_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.clear_btn = ctk.CTkButton(
            self.btn_frame, 
            text="Clear", 
            fg_color="gray30", 
            hover_color="gray40", 
            height=48,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.clear_form
        )
        self.clear_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # --- RIGHT PANEL: Battery Registry ---
        self.registry_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray12")
        self.registry_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.registry_frame.grid_columnconfigure(0, weight=1)
        self.registry_frame.grid_rowconfigure(2, weight=0)

        # Registry title
        reg_title = ctk.CTkLabel(self.registry_frame, text="BATTERY REGISTRY", font=ctk.CTkFont(size=14, weight="bold"))
        reg_title.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="w")

        # Search box
        search_frame = ctk.CTkFrame(self.registry_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=0)
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame, 
            placeholder_text="Search by Battery Name or Description...",
            height=38
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_batteries())

        clear_search_btn = ctk.CTkButton(
            search_frame, 
            text="Clear", 
            width=60, 
            height=38,
            fg_color="gray30", 
            command=self.clear_search
        )
        clear_search_btn.grid(row=0, column=1)

        # Registry Table
        self.table = ScrollableTable(
            self.registry_frame,
            headers=["Name", "Steps Count", "Status"],
            column_weights=[4, 2, 2],
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
            command=self.edit_selected_battery
        )
        self.edit_action_btn.pack(side="left", padx=10, pady=0)
        
        self.clone_action_btn = ctk.CTkButton(
            self.action_bar, text="Clone Selected", fg_color="gray30", hover_color="gray40",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.clone_selected_battery
        )
        self.clone_action_btn.pack(side="left", padx=10, pady=0)
        
        self.delete_action_btn = ctk.CTkButton(
            self.action_bar, text="Delete Selected", fg_color="#a83232", hover_color="#7a1e1e",
            height=45,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.delete_selected_batteries
        )
        self.delete_action_btn.pack(side="left", padx=10, pady=0)

        self.table_items = []
        self.load_batteries()

    def redraw_steps(self):
        """Re-render the list of test definition items in the sequence scroll pane."""
        # Cleanup
        for widget in self.steps_scroll.winfo_children():
            widget.destroy()

        if not self.sequence:
            lbl = ctk.CTkLabel(self.steps_scroll, text="No steps added yet. Select and click + Add.", text_color="gray50")
            lbl.pack(pady=30)
            return

        for idx, test_def in enumerate(self.sequence):
            step_frame = ctk.CTkFrame(self.steps_scroll, fg_color="gray18", corner_radius=4)
            step_frame.pack(fill="x", pady=2, padx=2)

            # Details
            lbl_text = f"{idx + 1}. {test_def.name} ({test_def.target_value} cNm)"
            lbl_def = ctk.CTkLabel(step_frame, text=lbl_text, font=ctk.CTkFont(size=11), anchor="w")
            lbl_def.pack(side="left", padx=10, fill="x", expand=True)

            # Operations buttons frame
            ops = ctk.CTkFrame(step_frame, fg_color="transparent")
            ops.pack(side="right", padx=5)

            # Up Button
            btn_up = ctk.CTkButton(
                ops, text="▲", width=22, height=22, fg_color="gray25", hover_color="gray35",
                state="disabled" if idx == 0 else "normal",
                command=lambda i=idx: self.move_step_up(i)
            )
            btn_up.pack(side="left", padx=1)

            # Down Button
            btn_down = ctk.CTkButton(
                ops, text="▼", width=22, height=22, fg_color="gray25", hover_color="gray35",
                state="disabled" if idx == len(self.sequence) - 1 else "normal",
                command=lambda i=idx: self.move_step_down(i)
            )
            btn_down.pack(side="left", padx=1)

            # Delete Button
            btn_del = ctk.CTkButton(
                ops, text="✕", width=22, height=22, fg_color="red4", hover_color="red3",
                command=lambda i=idx: self.delete_step(i)
            )
            btn_del.pack(side="left", padx=1)

    def add_step_to_sequence(self):
        choice = self.add_combo_var.get()
        test_def = self.test_def_map.get(choice)
        if test_def:
            self.sequence.append(test_def)
            self.redraw_steps()
            self.show_status("Added step to sequence.", "white")

    def move_step_up(self, idx):
        if idx > 0:
            self.sequence[idx], self.sequence[idx - 1] = self.sequence[idx - 1], self.sequence[idx]
            self.redraw_steps()

    def move_step_down(self, idx):
        if idx < len(self.sequence) - 1:
            self.sequence[idx], self.sequence[idx + 1] = self.sequence[idx + 1], self.sequence[idx]
            self.redraw_steps()

    def delete_step(self, idx):
        if 0 <= idx < len(self.sequence):
            self.sequence.pop(idx)
            self.redraw_steps()

    def show_status(self, text, color="white"):
        self.status_lbl.configure(text=text, text_color=color)

    def clear_search(self):
        self.search_entry.delete(0, "end")
        self.load_batteries()

    def clear_form(self, clear_selection=True):
        self.selected_battery_id = None
        self.name_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        self.active_var.set(True)
        self.sequence.clear()
        self.redraw_steps()
        self.show_status("", "white")
        
        if clear_selection:
            self.selected_battery_ids.clear()
            self.table.highlight_rows([])
            self.update_action_bar_visibility()

    def save_battery(self):
        name = self.name_entry.get().strip()
        desc = self.desc_entry.get().strip()
        active = self.active_var.get()

        if not name:
            self.show_status("Battery Name is required!", "red")
            return
        if not self.sequence:
            self.show_status("At least one test step must be added!", "red")
            return

        battery = TestBattery(
            id=self.selected_battery_id,
            name=name,
            description=desc,
            active=active
        )

        db_success = False
        action_str = ""
        
        if self.selected_battery_id:
            # Update existing
            db_success = self.app.db.update_battery(battery)
            action_str = "UPDATE_BATTERY"
        else:
            # Create new
            battery_id = self.app.db.create_battery(battery)
            if battery_id:
                battery.id = battery_id
                self.selected_battery_id = battery_id
                db_success = True
                action_str = "CREATE_BATTERY"

        if db_success:
            # Save items sequence
            test_def_ids = [td.id for td in self.sequence]
            set_items_success = self.app.db.set_battery_items(battery.id, test_def_ids)
            
            if set_items_success:
                log_action(
                    self.app.user_manager.current_user.username, 
                    action_str, 
                    f"Saved battery '{name}' with {len(test_def_ids)} steps."
                )
                self.clear_form()
                self.load_batteries()
                self.show_status("Battery saved successfully!", "green")
            else:
                self.show_status("Failed to save battery items sequence.", "red")
        else:
            self.show_status("Failed to save battery definition.", "red")

    def edit_battery_selected(self, battery: TestBattery):
        self.clear_form()
        self.selected_battery_id = battery.id
        self.name_entry.insert(0, battery.name)
        self.desc_entry.insert(0, battery.description)
        self.active_var.set(battery.active)

        # Load sequence
        items = self.app.db.get_battery_items(battery.id)
        self.sequence = [item.test_def for item in items if item.test_def]
        self.redraw_steps()
        self.show_status(f"Loaded battery: {battery.name}", "white")

    def clone_battery_selected(self, battery: TestBattery):
        self.edit_battery_selected(battery)
        self.selected_battery_id = None
        orig_name = self.name_entry.get()
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, f"Copy of {orig_name}")
        self.show_status(f"Cloned battery settings. Save to create new.", "white")

    def load_batteries(self):
        self.table.clear()
        batteries = self.app.db.get_all_batteries()

        # Apply search query
        query = self.search_entry.get().strip().lower()
        if query:
            batteries = [
                b for b in batteries
                if query in b.name.lower() or query in (b.description or "").lower()
            ]

        # Refresh dropdown active test lists in-memory
        test_defs = self.app.db.get_all_test_definitions()
        self.test_names = [td.name for td in test_defs if td.active]
        self.test_def_map = {td.name: td for td in test_defs if td.active}
        self.add_combo.configure(values=self.test_names)

        self.table_items = batteries

        counts_map = self.app.db.get_all_battery_item_counts()

        for b in batteries:
            # Count steps via single query map
            cnt = counts_map.get(b.id, 0)
            steps_count = f"{cnt} step(s)"
            active_disp = "Active" if b.active else "Inactive"
            text_color = "green" if b.active else "gray60"

            self.table.add_row(
                [
                    b.name,
                    steps_count,
                    active_disp
                ],
                text_color=text_color
            )
            
        # Re-apply highlights after loading rows
        selected_indices = [
            idx for idx, b in enumerate(self.table_items)
            if b.id in self.selected_battery_ids
        ]
        self.table.highlight_rows(selected_indices)

    def on_row_clicked(self, row_idx: int, ctrl_pressed: bool):
        if row_idx < len(self.table_items):
            selected_battery = self.table_items[row_idx]
            battery_id = selected_battery.id
            
            if ctrl_pressed:
                if battery_id in self.selected_battery_ids:
                    self.selected_battery_ids.discard(battery_id)
                else:
                    self.selected_battery_ids.add(battery_id)
            else:
                if len(self.selected_battery_ids) == 1 and battery_id in self.selected_battery_ids:
                    self.selected_battery_ids.clear()
                else:
                    self.selected_battery_ids.clear()
                    self.selected_battery_ids.add(battery_id)
            
            selected_indices = [
                idx for idx, b in enumerate(self.table_items)
                if b.id in self.selected_battery_ids
            ]
            self.table.highlight_rows(selected_indices)
            self.update_action_bar_visibility()
            
            if len(self.selected_battery_ids) == 1:
                active_id = list(self.selected_battery_ids)[0]
                active_b = next(b for b in self.table_items if b.id == active_id)
                self.edit_battery_selected(active_b)
            else:
                self.clear_form(clear_selection=False)

    def update_action_bar_visibility(self):
        count = len(self.selected_battery_ids)
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

    def edit_selected_battery(self):
        if len(self.selected_battery_ids) == 1:
            battery_id = list(self.selected_battery_ids)[0]
            battery = next(b for b in self.table_items if b.id == battery_id)
            self.edit_battery_selected(battery)

    def clone_selected_battery(self):
        if len(self.selected_battery_ids) == 1:
            battery_id = list(self.selected_battery_ids)[0]
            battery = next(b for b in self.table_items if b.id == battery_id)
            self.clone_battery_selected(battery)

    def delete_selected_batteries(self):
        from tkinter import messagebox
        count = len(self.selected_battery_ids)
        if count == 0:
            return
            
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the {count} selected battery configuration(s)?"
        )
        if not confirm:
            return
            
        success_count = 0
        deactivated_count = 0
        error_msgs = []
        
        battery_ids_to_delete = list(self.selected_battery_ids)
        
        for battery_id in battery_ids_to_delete:
            b_obj = next((b for b in self.table_items if b.id == battery_id), None)
            if not b_obj:
                continue
                
            try:
                self.app.db.delete_battery(battery_id)
                success_count += 1
                log_action(self.app.user_manager.current_user.username, "DELETE_BATTERY", f"Battery: {b_obj.name}")
            except Exception as e:
                # Handle foreign key constraint failure
                if "FOREIGN KEY" in str(e).upper() or "CONSTRAINT" in str(e).upper():
                    deactivate_confirm = messagebox.askyesno(
                        "Historical Logs Found",
                        f"Battery '{b_obj.name}' has historical test session logs and cannot be permanently deleted.\n\n"
                        "Would you like to deactivate it instead? (This will hide it from active test creation but keep the logs)."
                    )
                    if deactivate_confirm:
                        b_obj.active = False
                        if self.app.db.update_battery(b_obj):
                            deactivated_count += 1
                            log_action(self.app.user_manager.current_user.username, "DEACTIVATE_BATTERY", f"Battery: {b_obj.name}")
                        else:
                            error_msgs.append(f"Failed to deactivate '{b_obj.name}'")
                else:
                    error_msgs.append(f"Error deleting '{b_obj.name}': {e}")
                    
        self.clear_form(clear_selection=True)
        self.load_batteries()
        
        # Display completion status
        status_msg = f"Deleted {success_count} battery/batteries."
        if deactivated_count > 0:
            status_msg += f" Deactivated {deactivated_count} battery/batteries."
        if error_msgs:
            status_msg += f" Errors: {', '.join(error_msgs)}"
            self.show_status(status_msg, "red")
        else:
            self.show_status(status_msg, "green")
