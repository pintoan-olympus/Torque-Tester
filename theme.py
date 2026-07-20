"""
Theme & Design Tokens for Torque Tester Industrial HMI
Centralized design system tokens for high-contrast, touch-friendly UI components.
"""

class Colors:
    # Backgrounds
    BG_DARK = "#151515"
    BG_CARD = "#1e1e1e"
    BG_ROW_EVEN = "gray18"
    BG_ROW_ODD = "gray12"
    BG_CANVAS = "#242424"
    BG_SELECTION = "#1a73e8"
    
    # Status & Indicators
    PASS_GREEN = "#00A86B"
    PASS_HOVER = "#008E5A"
    FAIL_RED = "#FF0000"
    FAIL_HOVER = "#D32F2F"
    WARNING_YELLOW = "#FFD700"
    WARNING_ORANGE = "#FF9F00"
    INFO_CYAN = "cyan"
    
    # Buttons & Actions
    EDIT_BLUE = "#3a86ff"
    DELETE_RED = "#a83232"
    
    # Text
    TEXT_MAIN = "white"
    TEXT_MUTED = "gray60"
    TEXT_DARK = "gray15"
    TEXT_SECONDARY = "gray25"


class Fonts:
    TITLE_LARGE = ("Arial", 32, "bold")
    TITLE_MEDIUM = ("Arial", 24, "bold")
    HEADER = ("Arial", 14, "bold")
    BODY = ("Arial", 14)
    BODY_BOLD = ("Arial", 14, "bold")
    SMALL = ("Arial", 12)
    SMALL_BOLD = ("Arial", 12, "bold")
    CAPTION = ("Arial", 11, "bold")


class Dimensions:
    BTN_HEIGHT_LARGE = 60
    BTN_HEIGHT_ACTION = 48
    BTN_HEIGHT_TOP_BAR = 45
    INPUT_HEIGHT = 38
    TABLE_CELL_PADY = 10
    CORNER_RADIUS = 8
