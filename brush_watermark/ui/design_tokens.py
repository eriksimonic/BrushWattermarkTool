"""Design tokens for the "modern dark" editor UI.

Every UI color lives here; widgets import tokens and never hard-code hex
values (see ui/DESIGN.md). Accent colors are for interactive/active
affordances only: primary buttons, checked controls, slider fill, focus rings.
"""

# Surfaces
CANVAS_BG = "#0E0F11"
CANVAS_DOT = "#1C1E22"
CHROME = "#17181B"
FOOTER_BG = "#131416"
SURFACE_INPUT = "#1F2125"
SURFACE_RAISED = "#23252A"
SURFACE_RAISED_HOVER = "#2A2D33"
SURFACE_MENU = "#1D1F23"
SURFACE_SEGMENT = "#111214"
SURFACE_SEGMENT_ON = "#2E3137"

# Lines
BORDER = "#2C2F35"
BORDER_STRONG = "#33363C"
BORDER_HOVER = "#44474E"
DIVIDER = "#25272C"
KEY_BADGE_BORDER = "#34373D"
SWITCH_OFF = "#3A3D44"

# Text and icons
TEXT = "#ECEDEF"
TEXT_BODY = "#D5D7DB"
TEXT_SECONDARY = "#B4B7BE"
TEXT_LABEL = "#A1A4AB"
TEXT_MUTED = "#80848C"
TEXT_FAINT = "#4A4E55"
ICON_DISABLED = "#6E727A"

# Accent
ACCENT = "#3563E9"
ACCENT_HOVER = "#2C56D4"
ACCENT_BRIGHT = "#5B8CFF"
ACCENT_TEXT = "#9DBBFF"
ON_ACCENT = "#FFFFFF"
SLIDER_THUMB = "#FFFFFF"

# Status
WARNING = "#E0B25C"
SUCCESS = "#4CC38A"
DANGER_TEXT = "#F2A7A0"
SHADOW = "#000000"

# Canvas overlay colors (brush cursor, guides, anchor handles), drawn on top
# of photos, so they are chosen for contrast rather than to match the chrome.
HANDLE = "#C8C8C8"
ANCHOR_FILL = "#FFFFFF"
CANVAS_DRAWING = "#FACC15"
CANVAS_SPAN_START = "#22C55E"
CANVAS_SPAN_TRACK = "#86EFAC"
CANVAS_SPAN_END = "#F59E0B"
CANVAS_ERASER = "#F87171"

# Legacy names still imported by pre-redesign widgets; removed in Task 10.
PANEL = CHROME
INPUT = SURFACE_INPUT
BUTTON_HOVER = SURFACE_RAISED_HOVER
ACCENT_PRESSED = ACCENT_HOVER
SELECTION = SURFACE_RAISED_HOVER
SELECTION_BORDER = BORDER_HOVER
LINK = ACCENT_TEXT
SLIDER_HANDLE = SLIDER_THUMB
TRACK = BORDER_STRONG


def rgba(hex_color: str, alpha: float) -> str:
    """QSS ``rgba()`` string for a token at the given opacity (0–1)."""
    value = hex_color.lstrip("#")
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:g})"
