"""Zoom levels for the canvas: preset steps, clamping and parsing the typed %.

Pure functions (no Qt) so they can be unit-tested directly.
"""

from typing import Optional

ZOOM_MIN = 0.1
ZOOM_MAX = 4.0
# Zoom in/out walks these steps; a typed % can land anywhere in between.
ZOOM_STEPS = (0.1, 0.25, 0.33, 0.5, 0.67, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)


def clamp_zoom(scale: float) -> float:
    return max(ZOOM_MIN, min(ZOOM_MAX, float(scale)))


def step_zoom(scale: float, direction: int) -> float:
    """The next preset above (direction > 0) or below (direction < 0) `scale`."""
    # A small tolerance so 0.3301 counts as "at 33 %" and steps on to 50 %.
    eps = 1e-3
    if direction > 0:
        for step in ZOOM_STEPS:
            if step > scale + eps:
                return step
        return ZOOM_MAX
    for step in reversed(ZOOM_STEPS):
        if step < scale - eps:
            return step
    return ZOOM_MIN


def parse_zoom_percent(text: str) -> Optional[float]:
    """``"150"`` / ``"150%"`` / ``" 62 % "`` → scale (clamped); None if not a number."""
    raw = text.strip().rstrip("%").strip().replace(",", ".")
    try:
        percent = float(raw)
    except ValueError:
        return None
    if percent <= 0:
        return None
    return clamp_zoom(percent / 100.0)
