import customtkinter as ctk
import tkinter as tk
import math

class TorqueGauge(ctk.CTkFrame):
    """A custom gauge canvas widget that displays instantaneous and peak torque values."""
    def __init__(self, master, min_val=-50.0, max_val=50.0, target=0.0, tol_plus=0.0, tol_minus=0.0, **kwargs):
        super().__init__(master, **kwargs)
        
        self.min_val = min_val
        self.max_val = max_val
        self.target = target
        self.tol_plus = tol_plus
        self.tol_minus = tol_minus
        
        self.current_val = 0.0
        self.peak_val = 0.0
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1) # Canvas
        self.grid_rowconfigure(1, weight=0) # Readouts
        
        # Canvas sizes
        self.canvas_width = 240
        self.canvas_height = 150
        
        # Create Canvas
        # Color match with CTk gray15 (around #242424)
        self.canvas = tk.Canvas(
            self, 
            width=self.canvas_width, 
            height=self.canvas_height, 
            bg="#242424", 
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=0, pady=(10, 0))
        
        # Bottom text readouts
        self.readout_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.readout_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.readout_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.live_lbl = ctk.CTkLabel(
            self.readout_frame, 
            text="LIVE: 0.00 cNm", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.live_lbl.grid(row=0, column=0, padx=10)
        
        self.peak_lbl = ctk.CTkLabel(
            self.readout_frame, 
            text="PEAK: 0.00 cNm", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="amber" if hasattr(ctk, "amber") else "#ff9f0a"
        )
        self.peak_lbl.grid(row=0, column=1, padx=10)
        
        self.draw_gauge()

    def update_values(self, current, peak):
        self.current_val = current
        self.peak_val = peak
        
        self.live_lbl.configure(text=f"LIVE: {current:.2f} cNm")
        self.peak_lbl.configure(text=f"PEAK: {peak:.2f} cNm")
        
        self.draw_gauge()

    def set_tolerance_limits(self, target, plus, minus):
        self.target = target
        self.tol_plus = plus
        self.tol_minus = minus
        self.draw_gauge()

    def draw_gauge(self):
        self.canvas.delete("all")
        
        cx, cy = self.canvas_width / 2, self.canvas_height - 20
        r = 90  # Radius
        
        # Draw background arc (180 degrees, from pi to 2*pi)
        self.canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=0, extent=180,
            style="arc", outline="#444444", width=14
        )
        
        # Draw tolerance zone if target is set
        if self.target > 0:
            low = self.target - self.tol_minus
            high = self.target + self.tol_plus
            
            # Map values to angles (180 deg max, 0 is at right, 180 is at left)
            angle_low = self._val_to_angle(low)
            angle_high = self._val_to_angle(high)
            
            extent = angle_low - angle_high
            
            self.canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=angle_high, extent=extent,
                style="arc", outline="#00cc44", width=14
            )
            
            # Draw target tick mark
            angle_target = self._val_to_angle(self.target)
            rad = math.radians(angle_target)
            tx = cx + (r + 10) * math.cos(rad)
            ty = cy - (r + 10) * math.sin(rad)
            self.canvas.create_line(cx, cy, tx, ty, fill="#ffffff", width=2, dash=(4, 4))
            
        # Draw live value needle
        angle_curr = self._val_to_angle(self.current_val)
        rad_curr = math.radians(angle_curr)
        nx = cx + (r - 10) * math.cos(rad_curr)
        ny = cy - (r - 10) * math.sin(rad_curr)
        
        # Color needle according to tolerance check
        needle_color = "#3a86ff" # Blue default
        if self.target > 0:
            low = self.target - self.tol_minus
            high = self.target + self.tol_plus
            if low <= self.current_val <= high:
                needle_color = "#2ec4b6" # Teal OK
            elif self.current_val > high:
                needle_color = "#ff3333" # Red Too high
            elif self.current_val > 0.05:
                needle_color = "#ffb703" # Orange Too low but moving
                
        self.canvas.create_line(cx, cy, nx, ny, fill=needle_color, width=4)
        
        # Draw peak mark indicator
        if self.peak_val > 0:
            angle_peak = self._val_to_angle(self.peak_val)
            rad_peak = math.radians(angle_peak)
            px = cx + (r - 5) * math.cos(rad_peak)
            py = cy - (r - 5) * math.sin(rad_peak)
            # Small circle mark for peak
            self.canvas.create_oval(px-4, py-4, px+4, py+4, fill="#ff9f0a", outline="#ffffff", width=1)
            
        # Central hub cover
        self.canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill="#1a1a1a", outline="#444444", width=2)
        
        # Draw scale labels
        self.canvas.create_text(cx - r - 15, cy, text=f"{self.min_val:.0f}", fill="#aaaaaa", font=("Courier", 10))
        self.canvas.create_text(cx + r + 15, cy, text=f"{self.max_val:.0f}", fill="#aaaaaa", font=("Courier", 10))

    def _val_to_angle(self, val):
        """Map value to canvas arc angle (0 to 180). 180deg is left (min val), 0deg is right (max val)."""
        # Clamp value
        val = max(self.min_val, min(self.max_val, val))
        
        # Normalize between 0 and 1
        span = self.max_val - self.min_val
        if span == 0:
            return 90
            
        norm = (val - self.min_val) / span
        
        # Map to angles 180 (min) down to 0 (max)
        angle = 180 - (norm * 180)
        return angle


class ScrollableTable(ctk.CTkScrollableFrame):
    """A clean scrollable table widget that fits the modern theme."""
    def __init__(self, master, headers: list[str], column_weights: list[int] = None, row_click_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.headers = headers
        self.column_weights = column_weights or [1] * len(headers)
        self.row_click_callback = row_click_callback
        
        # Configure layout columns
        for col_idx, weight in enumerate(self.column_weights):
            self.grid_columnconfigure(col_idx, weight=weight)
            
        # Draw Header Row
        self.header_widgets = []
        for col_idx, header in enumerate(self.headers):
            lbl = ctk.CTkLabel(
                self, 
                text=header.upper(), 
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="gray60",
                anchor="w",
                padx=5,
                pady=8
            )
            lbl.grid(row=0, column=col_idx, sticky="ew", pady=(0, 5))
            self.header_widgets.append(lbl)
            
        # Storage for table row data
        self.row_widgets = []
        self.row_frames = []

    def clear(self):
        """Delete all records from table."""
        for row in self.row_widgets:
            for widget in row:
                if widget and widget.winfo_exists():
                    widget.destroy()
        for frame in self.row_frames:
            if frame and frame.winfo_exists():
                frame.destroy()
        self.row_widgets.clear()
        self.row_frames.clear()

    def highlight_rows(self, selected_indices: list[int]):
        """
        Highlight rows with selected_indices (0-based indices matching row_widgets).
        """
        for idx, frame in enumerate(self.row_frames):
            row_idx = idx + 1
            if frame and frame.winfo_exists():
                if idx in selected_indices:
                    frame.configure(fg_color="#1a73e8")  # Solid blue highlight
                else:
                    row_bg = "gray18" if row_idx % 2 == 0 else "gray12"
                    frame.configure(fg_color=row_bg)

    def add_row(self, cells: list[str], text_color=None, bg_color=None, cell_commands: dict = None):
        """
        Add a row to the table.
        cell_commands: dict of {col_index: callable} to make a cell clickable / be a button.
        """
        row_idx = len(self.row_widgets) + 1  # 1-indexed because headers are row 0
        widgets = []
        
        cell_commands = cell_commands or {}
        
        # Determine background color for row alternating
        row_bg = bg_color if bg_color else ("gray18" if row_idx % 2 == 0 else "gray12")
        
        row_frame = ctk.CTkFrame(self, fg_color=row_bg, corner_radius=4)
        row_frame.grid(row=row_idx, column=0, columnspan=len(self.headers), sticky="ew", pady=3)
        self.row_frames.append(row_frame)
        
        for col_idx, weight in enumerate(self.column_weights):
            row_frame.grid_columnconfigure(col_idx, weight=weight)
            
        for col_idx, val in enumerate(cells):
            if callable(val) and not isinstance(val, (str, bytes)):
                # If it is a widget factory (callable), call it with row_frame as master
                widget = val(row_frame)
            elif col_idx in cell_commands:
                # If command is provided, render a button instead of a label
                widget = ctk.CTkButton(
                    row_frame,
                    text=str(val),
                    font=ctk.CTkFont(size=13, weight="bold"),
                    height=32,
                    corner_radius=4,
                    command=cell_commands[col_idx]
                )
            else:
                widget = ctk.CTkLabel(
                    row_frame,
                    text=str(val),
                    font=ctk.CTkFont(size=14),
                    text_color=text_color or "white",
                    anchor="w",
                    padx=10,
                    pady=10
                )
            if isinstance(widget, ctk.CTkCheckBox):
                widget.grid(row=0, column=col_idx, sticky="w", padx=10)
            else:
                widget.grid(row=0, column=col_idx, sticky="ew", padx=1)
            
            # Bind click events for selection (except on interactive buttons)
            if self.row_click_callback and col_idx not in cell_commands:
                # 0-based index for the callback
                current_idx = row_idx - 1
                widget.bind("<Button-1>", lambda e, r_idx=current_idx: self.row_click_callback(r_idx, False))
                widget.bind("<Control-Button-1>", lambda e, r_idx=current_idx: self.row_click_callback(r_idx, True))
                
            widgets.append(widget)
            
        if self.row_click_callback:
            current_idx = row_idx - 1
            row_frame.bind("<Button-1>", lambda e, r_idx=current_idx: self.row_click_callback(r_idx, False))
            row_frame.bind("<Control-Button-1>", lambda e, r_idx=current_idx: self.row_click_callback(r_idx, True))
            
        self.row_widgets.append(widgets)
