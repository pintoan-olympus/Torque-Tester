import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from views.components import ScrollableTable
from theme import Colors, Fonts, Dimensions
from utils.logger import get_logger

logger = get_logger()

class BaseRegistryView(ctk.CTkFrame):
    """
    Base scaffold for registry CRUD views (DriverManager, TestSetup, BatterySetup).
    Provides common 2-column layout (form on left, search + scrollable table on right),
    top action bar management, multi-select handling, and selection highlighting.
    """
    def __init__(self, master, app, title: str, headers: list[str], column_weights: list[int] = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.title_text = title
        self.headers = headers
        self.column_weights = column_weights or [1] * len(headers)
        
        self.selected_ids = set()
        self.table_items = []
        self.last_clicked_idx = None

        self._build_layout()

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0) # Left form panel
        self.grid_columnconfigure(1, weight=1) # Right table panel
        self.grid_rowconfigure(0, weight=0)    # Header / Action bar
        self.grid_rowconfigure(1, weight=1)    # Content area

        self._build_header()
        self._build_left_form_frame()
        self._build_right_table_frame()

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CORNER_RADIUS)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 5))
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        # Title
        self.lbl_title = ctk.CTkLabel(
            self.header_frame,
            text=self.title_text,
            font=ctk.CTkFont(*Fonts.HEADER),
            text_color=Colors.TEXT_MAIN,
            padx=15,
            pady=10
        )
        self.lbl_title.grid(row=0, column=0, sticky="w")

        # Action bar container (hidden when 0 selected)
        self.action_bar = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.action_bar.grid(row=0, column=1, sticky="e", padx=10)
        self.action_bar.grid_remove() # Default hidden

        self.btn_edit = ctk.CTkButton(
            self.action_bar,
            text="Edit Selected",
            font=ctk.CTkFont(*Fonts.SMALL_BOLD),
            fg_color=Colors.EDIT_BLUE,
            height=Dimensions.BTN_HEIGHT_TOP_BAR,
            command=self.edit_selected
        )
        self.btn_edit.pack(side="left", padx=5)

        self.btn_clone = ctk.CTkButton(
            self.action_bar,
            text="Clone Selected",
            font=ctk.CTkFont(*Fonts.SMALL_BOLD),
            fg_color=Colors.BG_SELECTION,
            height=Dimensions.BTN_HEIGHT_TOP_BAR,
            command=self.clone_selected
        )
        self.btn_clone.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(
            self.action_bar,
            text="Delete Selected",
            font=ctk.CTkFont(*Fonts.SMALL_BOLD),
            fg_color=Colors.DELETE_RED,
            height=Dimensions.BTN_HEIGHT_TOP_BAR,
            command=self.delete_selected
        )
        self.btn_delete.pack(side="left", padx=5)

    def _build_left_form_frame(self):
        self.form_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CORNER_RADIUS)
        self.form_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=5)

    def _build_right_table_frame(self):
        self.table_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CORNER_RADIUS)
        self.table_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=5)
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=0) # Search bar
        self.table_frame.grid_rowconfigure(1, weight=1) # Table

        # Search Bar
        self.search_entry = ctk.CTkEntry(
            self.table_frame,
            placeholder_text="Search...",
            height=Dimensions.INPUT_HEIGHT,
            font=ctk.CTkFont(*Fonts.BODY)
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_data())

        # Scrollable Table
        self.table = ScrollableTable(
            self.table_frame,
            headers=self.headers,
            column_weights=self.column_weights,
            row_click_callback=self.on_row_clicked
        )
        self.table.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def on_row_clicked(self, row_idx: int, is_ctrl_click: bool = False):
        if row_idx < 0 or row_idx >= len(self.table_items):
            return

        item = self.table_items[row_idx]
        item_id = getattr(item, "id", None)

        if is_ctrl_click:
            if item_id in self.selected_ids:
                self.selected_ids.remove(item_id)
            else:
                self.selected_ids.add(item_id)
        else:
            self.selected_ids = {item_id}

        self.last_clicked_idx = row_idx
        self.update_action_bar_visibility()
        self.update_table_highlights()

    def update_action_bar_visibility(self):
        count = len(self.selected_ids)
        if count == 0:
            self.action_bar.grid_remove()
        else:
            self.action_bar.grid()
            if count == 1:
                self.btn_edit.configure(state="normal")
                self.btn_clone.configure(state="normal")
                self.btn_delete.configure(text="Delete Selected")
            else:
                self.btn_edit.configure(state="disabled")
                self.btn_clone.configure(state="disabled")
                self.btn_delete.configure(text=f"Delete ({count}) Selected")

    def update_table_highlights(self):
        selected_indices = [
            idx for idx, item in enumerate(self.table_items)
            if getattr(item, "id", None) in self.selected_ids
        ]
        self.table.highlight_rows(selected_indices)

    def load_data(self):
        """Override in subclass to fetch and populate table rows."""
        pass

    def edit_selected(self):
        """Override in subclass."""
        pass

    def clone_selected(self):
        """Override in subclass."""
        pass

    def delete_selected(self):
        """Override in subclass."""
        pass
