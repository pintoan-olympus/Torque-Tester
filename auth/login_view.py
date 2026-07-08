import customtkinter as ctk
from utils.logger import get_logger

logger = get_logger()

class LoginView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Configure layout: single column, centered rows
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)
        
        # Centered Login Card
        self.card = ctk.CTkFrame(self, width=400, height=350, corner_radius=15, fg_color="gray15")
        self.card.grid(row=1, column=0, sticky="ns")
        self.card.grid_propagate(False)
        
        # Align contents of the card
        self.card.grid_columnconfigure(0, weight=1)
        
        # Card Header
        self.title_lbl = ctk.CTkLabel(
            self.card, 
            text="Torque Quality Control", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_lbl.grid(row=0, column=0, pady=(30, 5), padx=20)
        
        self.subtitle_lbl = ctk.CTkLabel(
            self.card, 
            text="Please log in to proceed", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        )
        self.subtitle_lbl.grid(row=1, column=0, pady=(0, 20), padx=20)
        
        # Username Field
        self.username_entry = ctk.CTkEntry(
            self.card, 
            width=280, 
            placeholder_text="Username"
        )
        self.username_entry.grid(row=2, column=0, pady=10, padx=20)
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        
        # Password Field
        self.password_entry = ctk.CTkEntry(
            self.card, 
            width=280, 
            placeholder_text="Password", 
            show="*"
        )
        self.password_entry.grid(row=3, column=0, pady=10, padx=20)
        self.password_entry.bind("<Return>", lambda e: self.handle_login())
        
        # Error / Status message
        self.status_lbl = ctk.CTkLabel(
            self.card, 
            text="", 
            font=ctk.CTkFont(size=12), 
            text_color="red"
        )
        self.status_lbl.grid(row=4, column=0, pady=5, padx=20)
        
        # Login Button
        self.login_btn = ctk.CTkButton(
            self.card, 
            text="Login", 
            width=280, 
            height=35, 
            font=ctk.CTkFont(weight="bold"), 
            command=self.handle_login
        )
        self.login_btn.grid(row=5, column=0, pady=(15, 20), padx=20)

    def handle_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            self.status_lbl.configure(text="Please fill in all fields.")
            return
            
        self.login_btn.configure(state="disabled", text="Authenticating...")
        self.update_idletasks()
        
        success = self.app.user_manager.login(username, password)
        
        if success:
            logger.info(f"User {username} logged in successfully.")
            self.app.on_login_success()
        else:
            self.login_btn.configure(state="normal", text="Login")
            self.status_lbl.configure(text="Invalid username or password.")
            self.password_entry.delete(0, 'end')
            self.password_entry.focus()
