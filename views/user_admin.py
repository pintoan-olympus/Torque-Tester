import customtkinter as ctk
import config
from utils.logger import get_logger, log_action
from views.components import ScrollableTable
from database.models import User

logger = get_logger()

class UserAdminView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Selected user ID for editing (None means adding new)
        self.selected_user_id = None
        
        # Grid layout (2 columns: left form, right registry table)
        self.grid_columnconfigure(0, weight=2, uniform="cols")
        self.grid_columnconfigure(1, weight=3, uniform="cols")
        self.grid_rowconfigure(0, weight=1)
        
        # --- LEFT PANEL: User Form ---
        self.form_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        self.form_title = ctk.CTkLabel(
            self.form_frame, 
            text="CREATE NEW USER", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.form_title.pack(pady=(15, 10), padx=20, anchor="w")
        
        # Username
        ctk.CTkLabel(self.form_frame, text="Username:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=20, anchor="w")
        self.username_entry = ctk.CTkEntry(self.form_frame, placeholder_text="e.g. jsmith")
        self.username_entry.pack(fill="x", padx=20, pady=(0, 5))
        
        # Password
        self.pwd_lbl = ctk.CTkLabel(self.form_frame, text="Password:", font=ctk.CTkFont(size=11, weight="bold"))
        self.pwd_lbl.pack(pady=(5, 1), padx=20, anchor="w")
        self.password_entry = ctk.CTkEntry(self.form_frame, placeholder_text="Password", show="*")
        self.password_entry.pack(fill="x", padx=20, pady=(0, 5))
        
        # Full Name
        ctk.CTkLabel(self.form_frame, text="Full Name:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=20, anchor="w")
        self.name_entry = ctk.CTkEntry(self.form_frame, placeholder_text="e.g. John Smith")
        self.name_entry.pack(fill="x", padx=20, pady=(0, 5))
        
        # Access Level
        ctk.CTkLabel(self.form_frame, text="Access Level:", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(5, 1), padx=20, anchor="w")
        self.level_combo = ctk.CTkComboBox(self.form_frame, values=["Operator", "Supervisor", "Admin"])
        self.level_combo.pack(fill="x", padx=20, pady=(0, 5))
        
        # Active Checkbox
        self.active_var = ctk.BooleanVar(value=True)
        self.active_cb = ctk.CTkCheckBox(self.form_frame, text="Account Active / Enabled", variable=self.active_var)
        self.active_cb.pack(pady=10, padx=20, anchor="w")
        
        # Form Status
        self.status_lbl = ctk.CTkLabel(self.form_frame, text="", text_color="red", font=ctk.CTkFont(size=12))
        self.status_lbl.pack(pady=5)
        
        # Form Buttons
        self.form_btn_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        self.form_btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        self.form_btn_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.save_btn = ctk.CTkButton(
            self.form_btn_frame, 
            text="Save User", 
            fg_color="green", 
            hover_color="darkgreen",
            command=self.save_user
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
        
        # --- RIGHT PANEL: User List Registry ---
        self.registry_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="gray15")
        self.registry_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.registry_frame.grid_columnconfigure(0, weight=1)
        self.registry_frame.grid_rowconfigure(1, weight=1)
        
        # Registry Title
        reg_title = ctk.CTkLabel(self.registry_frame, text="USER ACCOUNT REGISTRY", font=ctk.CTkFont(size=14, weight="bold"))
        reg_title.grid(row=0, column=0, pady=(15, 10), padx=20, sticky="w")
        
        # Table
        self.table = ScrollableTable(
            self.registry_frame,
            headers=["Username", "Full Name", "Access Level", "Status", "Edit"],
            column_weights=[2, 3, 2, 2, 1],
            fg_color="gray12"
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        
        self.load_users()

    def load_users(self):
        self.table.clear()
        users = self.app.db.get_all_users()
        
        for u in users:
            level_name = config.ACCESS_LEVEL_NAMES.get(u.access_level, "Operator")
            status_disp = "Active" if u.active else "Inactive"
            row_color = "green" if u.active else "gray60"
            
            cell_commands = {
                4: lambda u_obj=u: self.edit_user_selected(u_obj)
            }
            
            self.table.add_row(
                [
                    u.username,
                    u.full_name,
                    level_name,
                    status_disp,
                    "Edit"
                ],
                text_color=row_color,
                cell_commands=cell_commands
            )

    def edit_user_selected(self, user: User):
        self.selected_user_id = user.id
        self.form_title.configure(text=f"EDIT USER: {user.username.upper()}")
        
        # Lock username field
        self.username_entry.configure(state="normal")
        self.username_entry.delete(0, "end")
        self.username_entry.insert(0, user.username)
        self.username_entry.configure(state="disabled")
        
        # Adjust password field instruction
        self.pwd_lbl.configure(text="Reset Password (leave blank to keep):")
        self.password_entry.delete(0, "end")
        
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, user.full_name)
        
        # Set combobox level mapping
        level_name = config.ACCESS_LEVEL_NAMES.get(user.access_level, "Operator")
        self.level_combo.set(level_name)
        
        self.active_var.set(user.active)
        self.status_lbl.configure(text="")

    def clear_form(self):
        self.selected_user_id = None
        self.form_title.configure(text="CREATE NEW USER")
        
        self.username_entry.configure(state="normal")
        self.username_entry.delete(0, "end")
        
        self.pwd_lbl.configure(text="Password:")
        self.password_entry.delete(0, "end")
        
        self.name_entry.delete(0, "end")
        self.level_combo.set("Operator")
        self.active_var.set(True)
        self.status_lbl.configure(text="")

    def save_user(self):
        # Validate inputs
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        full_name = self.name_entry.get().strip()
        level_str = self.level_combo.get()
        active = self.active_var.get()
        
        # Map string back to access level integer
        level_map = {"Operator": config.ACCESS_OPERATOR, "Supervisor": config.ACCESS_SUPERVISOR, "Admin": config.ACCESS_ADMIN}
        access_level = level_map.get(level_str, config.ACCESS_OPERATOR)
        
        if not username or not full_name:
            self.status_lbl.configure(text="Username and Full Name are required.")
            return
            
        # If adding a new user, password is required
        if not self.selected_user_id and not password:
            self.status_lbl.configure(text="Password is required for new users.")
            return
            
        if self.selected_user_id:
            # Update user profile details
            success = self.app.user_manager.update_user_profile(
                self.selected_user_id, 
                full_name, 
                access_level, 
                active
            )
            
            # If password is filled in, also update password
            if password:
                self.app.user_manager.change_password(self.selected_user_id, password)
                
            action_log = "UPDATE_USER_ACCOUNT"
        else:
            # Create new user
            success = self.app.user_manager.create_user(
                username, 
                password, 
                full_name, 
                access_level
            )
            action_log = "CREATE_USER_ACCOUNT"
            
        if success:
            log_action(self.app.user_manager.current_user.username, action_log, f"Account: {username}")
            self.clear_form()
            self.load_users()
        else:
            self.status_lbl.configure(text="Operation failed. Username may already exist.")
