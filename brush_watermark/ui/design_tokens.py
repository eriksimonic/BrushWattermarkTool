"""Lightroom-inspired UI tokens with a blue accent layer for interactive states.

ACCENT colors are for interactive/active affordances only (primary buttons,
checked checkboxes/tool buttons, slider fill, focus rings) — do not use them
for static chrome/panel backgrounds, body text, or list-row selection.
"""

CANVAS_BG = "#2A2A2A"
CHROME = "#333333"
PANEL = "#3B3B3B"
INPUT = "#454545"
BORDER = "#505050"
DIVIDER = "#555555"
TEXT = "#D4D4D4"
TEXT_SECONDARY = "#A8A8A8"
TEXT_MUTED = "#808080"
HANDLE = "#C8C8C8"
SLIDER_HANDLE = "#F0F0F0"
TRACK = "#606060"
SELECTION = "#565656"
SELECTION_BORDER = "#909090"
LINK = "#A8C4DC"
BUTTON_HOVER = "#4A4A4A"

ACCENT = "#3D7FFF"
ACCENT_HOVER = "#5C93FF"
ACCENT_PRESSED = "#2E63CC"
ON_ACCENT = "#FFFFFF"

# Canvas overlay colors (brush cursor, guides, anchor handles) — distinct from
# the chrome/interactive tokens above since they're drawn on top of photos.
CANVAS_DRAWING = "#FACC15"
CANVAS_SPAN_START = "#22C55E"
CANVAS_SPAN_TRACK = "#86EFAC"
CANVAS_SPAN_END = "#F59E0B"
CANVAS_ERASER = "#F87171"
CANVAS_ANCHOR_OUTLINE = "#000000"
