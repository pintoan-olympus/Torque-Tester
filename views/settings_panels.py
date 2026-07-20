import customtkinter as ctk
from theme import Colors, Fonts, Dimensions
from utils.logger import get_logger, log_action

logger = get_logger()

class SensorSettingsPanel(ctk.CTkFrame):
    """Sub-panel for Hardware & Sensor Configuration."""
    def __init__(self, master, settings_view, **kwargs):
        super().__init__(master, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CORNER_RADIUS, **kwargs)
        self.settings_view = settings_view
        self._build_ui()

    def _build_ui(self):
        lbl = ctk.CTkLabel(
            self,
            text="HARDWARE & SENSOR CONFIGURATION",
            font=ctk.CTkFont(*Fonts.HEADER),
            text_color=Colors.TEXT_MAIN
        )
        lbl.pack(anchor="w", padx=15, pady=10)


class DatabaseSettingsPanel(ctk.CTkFrame):
    """Sub-panel for Database Connection Settings (SQLite / SQL Server)."""
    def __init__(self, master, settings_view, **kwargs):
        super().__init__(master, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CORNER_RADIUS, **kwargs)
        self.settings_view = settings_view
        self._build_ui()

    def _build_ui(self):
        lbl = ctk.CTkLabel(
            self,
            text="DATABASE CONNECTION SETTINGS",
            font=ctk.CTkFont(*Fonts.HEADER),
            text_color=Colors.TEXT_MAIN
        )
        lbl.pack(anchor="w", padx=15, pady=10)


class LogExportSettingsPanel(ctk.CTkFrame):
    """Sub-panel for Logs, Audit Trail & CSV Data Management."""
    def __init__(self, master, settings_view, **kwargs):
        super().__init__(master, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CORNER_RADIUS, **kwargs)
        self.settings_view = settings_view
        self._build_ui()

    def _build_ui(self):
        lbl = ctk.CTkLabel(
            self,
            text="SYSTEM LOGS & DATA MANAGEMENT",
            font=ctk.CTkFont(*Fonts.HEADER),
            text_color=Colors.TEXT_MAIN
        )
        lbl.pack(anchor="w", padx=15, pady=10)
