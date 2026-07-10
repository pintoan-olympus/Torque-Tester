import customtkinter as ctk
from utils.logger import get_logger
import i18n

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
        self.card = ctk.CTkFrame(self, width=400, height=420, corner_radius=15, fg_color="gray15")
        self.card.grid(row=1, column=0, sticky="ns")
        self.card.grid_propagate(False)
        
        # Align contents of the card
        self.card.grid_columnconfigure(0, weight=1)
        
        # Card Header
        self.title_lbl = ctk.CTkLabel(
            self.card, 
            text="", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.title_lbl.grid(row=0, column=0, pady=(25, 5), padx=20)
        
        self.subtitle_lbl = ctk.CTkLabel(
            self.card, 
            text="", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        )
        self.subtitle_lbl.grid(row=1, column=0, pady=(0, 15), padx=20)
        
        # Language segmented button
        self.lang_var = ctk.StringVar(value="English" if i18n.get_language() == "en" else "Português")
        self.lang_btn = ctk.CTkSegmentedButton(
            self.card,
            values=["English", "Português"],
            variable=self.lang_var,
            command=self.change_language,
            width=280
        )
        self.lang_btn.grid(row=2, column=0, pady=(0, 15), padx=20)
        
        # Username Field
        self.username_entry = ctk.CTkEntry(
            self.card, 
            width=280
        )
        self.username_entry.grid(row=3, column=0, pady=10, padx=20)
        self.username_entry.bind("<Return>", lambda e: self.password_entry.focus())
        
        # Password Field
        self.password_entry = ctk.CTkEntry(
            self.card, 
            width=280, 
            show="*"
        )
        self.password_entry.grid(row=4, column=0, pady=10, padx=20)
        self.password_entry.bind("<Return>", lambda e: self.handle_login())
        
        # Error / Status message
        self.status_lbl = ctk.CTkLabel(
            self.card, 
            text="", 
            font=ctk.CTkFont(size=12), 
            text_color="red"
        )
        self.status_lbl.grid(row=5, column=0, pady=5, padx=20)
        
        # Login Button
        self.login_btn = ctk.CTkButton(
            self.card, 
            text="", 
            width=280, 
            height=35, 
            font=ctk.CTkFont(weight="bold"), 
            command=self.handle_login
        )
        self.login_btn.grid(row=6, column=0, pady=(10, 20), padx=20)

        # Apply initial translations
        self.refresh_texts()

    def change_language(self, val):
        lang = "en" if val == "English" else "pt"
        i18n.set_language(lang)
        self.app.hw_config.set_setting("language", lang)
        self.refresh_texts()

    def refresh_texts(self):
        self.title_lbl.configure(text=i18n.t("login.title"))
        self.subtitle_lbl.configure(text=i18n.t("login.subtitle"))
        self.username_entry.configure(placeholder_text=i18n.t("login.username"))
        self.password_entry.configure(placeholder_text=i18n.t("login.password"))
        self.login_btn.configure(text=i18n.t("login.btn"))
        if self.status_lbl.cget("text") != "":
            self.status_lbl.configure(text=i18n.t("login.error"))

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
            self.login_btn.configure(state="normal", text=i18n.t("login.btn"))
            self.status_lbl.configure(text=i18n.t("login.error"))
            self.password_entry.delete(0, 'end')
            self.password_entry.focus()
